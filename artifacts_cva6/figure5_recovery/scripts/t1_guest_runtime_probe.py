#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RECOVERY_DIR = SCRIPT_DIR.parent
ARTIFACTS_DIR = RECOVERY_DIR.parent
REPO_DIR = ARTIFACTS_DIR.parent
RESULTS_DIR = RECOVERY_DIR / "results"
LOGS_DIR = RECOVERY_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OUT_LOG = LOGS_DIR / "t1_guest_runtime_probe.log"
OUT_JSON = RESULTS_DIR / "t1_guest_runtime_probe.json"
OUT_MD = RESULTS_DIR / "t1_guest_runtime_probe.md"
FALLBACK_LOG = Path("/tmp/sharcbridge_cva6_runtime/persistent_session.log")

SDK_DIR = Path(os.environ.get("CVA6_SDK_DIR", REPO_DIR / "CVA6_LINUX" / "cva6-sdk"))
SPIKE_BIN = Path(os.environ.get("CVA6_SPIKE_BIN", SDK_DIR / "install64" / "bin" / "spike"))
SPIKE_PAYLOAD = Path(os.environ.get("CVA6_SPIKE_PAYLOAD", SDK_DIR / "install64" / "spike_fw_payload.elf"))
BOOT_TIMEOUT_S = float(os.environ.get("T1_SPIKE_BOOT_TIMEOUT_S", "150"))
COMMAND_TIMEOUT_S = float(os.environ.get("T1_SPIKE_COMMAND_TIMEOUT_S", "30"))
SHELL_PROMPT = os.environ.get("CVA6_SPIKE_SHELL_PROMPT", "# ")
BEGIN_MARKER = "__T1_GUEST_PROBE_BEGIN__"
END_MARKER = "__T1_GUEST_PROBE_END__"


def read_until(
    proc: subprocess.Popen[bytes],
    selector: selectors.BaseSelector,
    markers: list[str],
    timeout_s: float,
    chunks: list[str],
) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        events = selector.select(timeout=0.2)
        if not events:
            if proc.poll() is not None:
                raise RuntimeError(f"Spike exited with code {proc.returncode} before markers {markers}")
            continue
        for key, _ in events:
            chunk = key.fileobj.read(4096)
            if not chunk:
                if proc.poll() is not None:
                    raise RuntimeError(f"Spike exited with code {proc.returncode} before markers {markers}")
                continue
            text = chunk.decode("utf-8", errors="ignore")
            chunks.append(text)
            joined = "".join(chunks)
            for marker in markers:
                if marker in joined:
                    return joined
    raise RuntimeError(f"Timeout waiting for markers {markers}")


def build_probe_command() -> str:
    lines = [
        f"echo {BEGIN_MARKER}",
        "if [ -e /usr/bin/sharc_cva6_acc_runtime ]; then echo runtime_exists=yes; else echo runtime_exists=no; fi",
        "if [ -x /usr/bin/sharc_cva6_acc_runtime ]; then echo runtime_execbit=yes; else echo runtime_execbit=no; fi",
        "if [ -e /usr/share/sharcbridge_cva6/base_config.json ]; then echo base_config_exists=yes; else echo base_config_exists=no; fi",
        "if [ -e /lib/ld-linux-riscv64-lp64d.so.1 ]; then echo loader_lp64d=yes; else echo loader_lp64d=no; fi",
        "ls -l /usr/bin/sharc_cva6_acc_runtime 2>&1 || true",
        "ls -l /usr/share/sharcbridge_cva6/base_config.json 2>&1 || true",
        "(/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json /tmp/t1_missing_snapshot.json) >/tmp/t1_runtime_exec.out 2>&1 || true",
        "cat /tmp/t1_runtime_exec.out 2>&1 || true",
        f"echo {END_MARKER}",
    ]
    return "\n".join(lines) + "\n"


def classify(payload_text: str) -> str:
    runtime_exists = "runtime_exists=yes" in payload_text
    runtime_execbit = "runtime_execbit=yes" in payload_text
    loader_exists = "loader_lp64d=yes" in payload_text
    exec_not_found = "not found" in payload_text

    if not runtime_exists:
        return "runtime_absent"
    if runtime_exists and runtime_execbit and not loader_exists:
        return "runtime_present_but_loader_missing"
    if runtime_exists and exec_not_found and not loader_exists:
        return "runtime_present_but_loader_missing"
    if runtime_exists and runtime_execbit:
        return "runtime_present_and_executable"
    return "runtime_present_but_not_executable"


def classify_from_fallback_log(text: str) -> tuple[str, dict]:
    details = {
        "runtime_exists": None,
        "runtime_execbit": None,
        "base_config_exists": None,
        "loader_lp64d_exists": None,
        "exec_not_found": "not found" in text,
    }

    if "__SHARCBRIDGE_RUNTIME_MISSING__" in text:
        details["runtime_exists"] = False
        details["runtime_execbit"] = False
        return "runtime_absent", details

    if "__SHARCBRIDGE_RUNTIME_OK__" in text and "not found" in text:
        details["runtime_exists"] = True
        details["runtime_execbit"] = True
        return "runtime_present_but_loader_missing", details

    if "__SHARCBRIDGE_RUNTIME_OK__" in text:
        details["runtime_exists"] = True
        details["runtime_execbit"] = True
        return "runtime_present_and_executable", details

    return "probe_failed", details


def main() -> int:
    if not SPIKE_BIN.is_file():
        raise SystemExit(f"Missing spike binary: {SPIKE_BIN}")
    if not SPIKE_PAYLOAD.is_file():
        raise SystemExit(f"Missing spike payload: {SPIKE_PAYLOAD}")

    proc = subprocess.Popen(
        [str(SPIKE_BIN), str(SPIKE_PAYLOAD)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    selector = selectors.DefaultSelector()
    chunks: list[str] = []
    payload_text = ""
    error: str | None = None

    try:
        if proc.stdout is None or proc.stdin is None:
            raise RuntimeError("Failed to open Spike stdio streams")

        selector.register(proc.stdout, selectors.EVENT_READ)
        read_until(proc, selector, ["Run /init as init process", SHELL_PROMPT], BOOT_TIMEOUT_S, chunks)

        proc.stdin.write(build_probe_command().encode("utf-8"))
        proc.stdin.flush()
        joined = read_until(proc, selector, [END_MARKER], COMMAND_TIMEOUT_S, chunks)
        begin = joined.find(BEGIN_MARKER)
        end = joined.find(END_MARKER, begin if begin != -1 else 0)
        if begin != -1 and end != -1:
            payload_text = joined[begin + len(BEGIN_MARKER) : end]
        else:
            raise RuntimeError("Could not isolate guest probe payload")
    except Exception as exc:
        error = str(exc)
    finally:
        OUT_LOG.write_text("".join(chunks), encoding="utf-8")
        try:
            selector.close()
        except Exception:
            pass
        try:
            if proc.poll() is None and proc.stdin is not None:
                try:
                    proc.stdin.write(b"poweroff -f\n")
                    proc.stdin.flush()
                except Exception:
                    pass
                time.sleep(0.2)
                if proc.poll() is None:
                    proc.kill()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "spike_bin": str(SPIKE_BIN),
        "spike_payload": str(SPIKE_PAYLOAD),
        "log_path": str(OUT_LOG),
        "error": error,
        "probe_excerpt": payload_text.strip(),
        "fallback_log": str(FALLBACK_LOG),
    }

    if error is None:
        classification = classify(payload_text)
        report["classification"] = classification
        report["runtime_exists"] = "runtime_exists=yes" in payload_text
        report["runtime_execbit"] = "runtime_execbit=yes" in payload_text
        report["base_config_exists"] = "base_config_exists=yes" in payload_text
        report["loader_lp64d_exists"] = "loader_lp64d=yes" in payload_text
        report["exec_not_found"] = "not found" in payload_text
        passed = classification == "runtime_present_and_executable"
    else:
        if FALLBACK_LOG.is_file():
            fallback_text = FALLBACK_LOG.read_text(encoding="utf-8", errors="ignore")
            classification, details = classify_from_fallback_log(fallback_text)
            report["classification"] = classification
            report["classification_source"] = "fallback_log"
            report["runtime_exists"] = details["runtime_exists"]
            report["runtime_execbit"] = details["runtime_execbit"]
            report["base_config_exists"] = details["base_config_exists"]
            report["loader_lp64d_exists"] = details["loader_lp64d_exists"]
            report["exec_not_found"] = details["exec_not_found"]
            report["fallback_excerpt"] = fallback_text[-4000:]
            passed = classification == "runtime_present_and_executable"
        else:
            report["classification"] = "probe_failed"
            passed = False

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# T1 Guest Runtime Probe",
                "",
                f"- status: `{'PASS' if passed else 'FAIL'}`",
                f"- classification: `{report['classification']}`",
                f"- spike_bin: `{report['spike_bin']}`",
                f"- spike_payload: `{report['spike_payload']}`",
                f"- log_path: `{report['log_path']}`",
                f"- runtime_exists: `{report.get('runtime_exists')}`",
                f"- runtime_execbit: `{report.get('runtime_execbit')}`",
                f"- base_config_exists: `{report.get('base_config_exists')}`",
                f"- loader_lp64d_exists: `{report.get('loader_lp64d_exists')}`",
                f"- exec_not_found: `{report.get('exec_not_found')}`",
                f"- error: `{report.get('error')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
