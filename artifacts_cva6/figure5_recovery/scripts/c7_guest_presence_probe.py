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

OUT_LOG = LOGS_DIR / "c7_guest_presence_probe.log"
OUT_JSON = RESULTS_DIR / "c7_guest_presence_probe.json"
OUT_MD = RESULTS_DIR / "c7_guest_presence_probe.md"

SDK_DIR = Path(os.environ.get("CVA6_SDK_DIR", REPO_DIR / "CVA6_LINUX" / "cva6-sdk"))
SPIKE_BIN = Path(os.environ.get("CVA6_SPIKE_BIN", SDK_DIR / "install64" / "bin" / "spike"))
SPIKE_PAYLOAD = Path(os.environ.get("CVA6_SPIKE_PAYLOAD", SDK_DIR / "install64" / "spike_fw_payload.elf"))
BOOT_TIMEOUT_S = float(os.environ.get("C7_SPIKE_BOOT_TIMEOUT_S", "120"))
COMMAND_TIMEOUT_S = float(os.environ.get("C7_SPIKE_COMMAND_TIMEOUT_S", "45"))

BOOT_MARKERS = ["Starting sshd: OK", "NFS preparation skipped, OK", "# "]
BEGIN_MARKER = "__C7_GUEST_BEGIN__"
END_MARKER = "__C7_GUEST_END__"


def read_until_all(
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
            if all(marker in joined for marker in markers):
                return joined
    raise RuntimeError(f"Timeout waiting for markers {markers}")


def read_until_marker(
    proc: subprocess.Popen[bytes],
    selector: selectors.BaseSelector,
    marker: str,
    timeout_s: float,
    chunks: list[str],
) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        events = selector.select(timeout=0.2)
        if not events:
            if proc.poll() is not None:
                raise RuntimeError(f"Spike exited with code {proc.returncode} before marker {marker}")
            continue
        for key, _ in events:
            chunk = key.fileobj.read(4096)
            if not chunk:
                if proc.poll() is not None:
                    raise RuntimeError(f"Spike exited with code {proc.returncode} before marker {marker}")
                continue
            text = chunk.decode("utf-8", errors="ignore")
            chunks.append(text)
            joined = "".join(chunks)
            if marker in joined:
                return joined
    raise RuntimeError(f"Timeout waiting for marker {marker}")


def build_probe_command() -> str:
    lines = [
        f"echo {BEGIN_MARKER}",
        "for p in /usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json /lib/ld-linux-riscv64-lp64d.so.1; do if [ -e \"$p\" ]; then echo EXISTS:$p; ls -l \"$p\"; else echo MISSING:$p; fi; done",
        "cat > /tmp/c7_snapshot.json <<'JSON'",
        '{"snapshot_id":"c7","k":0,"t":0.0,"x":[0.0,60.0,15.0],"w":[11.0,1.0],"u_prev":[0.0,0.0]}',
        "JSON",
        "(/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json /tmp/c7_snapshot.json) >/tmp/c7_runtime_exec.out 2>&1 || true",
        "cat /tmp/c7_runtime_exec.out 2>&1 || true",
        f"echo {END_MARKER}",
    ]
    return "\n".join(lines) + "\n"


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
        read_until_all(proc, selector, BOOT_MARKERS, BOOT_TIMEOUT_S, chunks)

        proc.stdin.write(build_probe_command().encode("utf-8"))
        proc.stdin.flush()
        joined = read_until_marker(proc, selector, END_MARKER, COMMAND_TIMEOUT_S, chunks)
        begin = joined.find(BEGIN_MARKER)
        end = joined.find(END_MARKER, begin if begin != -1 else 0)
        if begin == -1 or end == -1:
            raise RuntimeError("Could not isolate guest probe payload")
        payload_text = joined[begin + len(BEGIN_MARKER) : end]
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
    }

    runtime_exists = "EXISTS:/usr/bin/sharc_cva6_acc_runtime" in payload_text
    base_config_exists = "EXISTS:/usr/share/sharcbridge_cva6/base_config.json" in payload_text
    loader_exists = "EXISTS:/lib/ld-linux-riscv64-lp64d.so.1" in payload_text
    runtime_success = '"status": "SUCCESS"' in payload_text or "status: 0 (opt code: 1)" in payload_text
    exec_not_found = "not found" in payload_text

    report.update(
        {
            "runtime_exists": runtime_exists,
            "base_config_exists": base_config_exists,
            "loader_lp64d_exists": loader_exists,
            "runtime_success": runtime_success,
            "exec_not_found": exec_not_found,
        }
    )

    if error is not None:
        classification = "probe_failed"
    elif runtime_exists and base_config_exists and loader_exists and runtime_success:
        classification = "runtime_present_and_executable"
    elif runtime_exists and base_config_exists and loader_exists:
        classification = "runtime_present_but_execution_unclear"
    else:
        classification = "runtime_absent_in_live_guest"

    report["classification"] = classification
    passed = classification == "runtime_present_and_executable"

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# C7 Guest Presence Probe",
                "",
                f"- status: `{'PASS' if passed else 'FAIL'}`",
                f"- classification: `{classification}`",
                f"- spike_bin: `{SPIKE_BIN}`",
                f"- spike_payload: `{SPIKE_PAYLOAD}`",
                f"- log_path: `{OUT_LOG}`",
                f"- runtime_exists: `{runtime_exists}`",
                f"- base_config_exists: `{base_config_exists}`",
                f"- loader_lp64d_exists: `{loader_exists}`",
                f"- runtime_success: `{runtime_success}`",
                f"- exec_not_found: `{exec_not_found}`",
                f"- error: `{error}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
