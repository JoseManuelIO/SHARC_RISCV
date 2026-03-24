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
RESULTS_DIR = RECOVERY_DIR / "results"
LOGS_DIR = RECOVERY_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = RESULTS_DIR / "r5_guest_boot_probe.json"
OUT_MD = RESULTS_DIR / "r5_guest_boot_probe.md"
OUT_LOG = LOGS_DIR / "r5_guest_boot_probe.log"

SPIKE_BIN = Path(
    os.environ.get(
        "R5_SPIKE_BIN",
        "/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/bin/spike",
    )
)
SPIKE_PAYLOAD = Path(
    os.environ.get(
        "R5_SPIKE_PAYLOAD",
        "/tmp/cva6-sdk-clean-20260324-r1-2/install64/spike_fw_payload.elf",
    )
)
BOOT_TIMEOUT_S = float(os.environ.get("R5_BOOT_TIMEOUT_S", "90"))
PROMPT_TIMEOUT_S = float(os.environ.get("R5_PROMPT_TIMEOUT_S", "30"))
PROMPT = os.environ.get("R5_PROMPT", "# ")

BOOT_MARKERS = [
    "Run /init as init process",
    "Starting sshd: OK",
    PROMPT,
]


def read_until(
    proc: subprocess.Popen,
    selector: selectors.BaseSelector,
    markers: list[str],
    timeout_s: float,
    log_handle,
) -> str:
    deadline = time.monotonic() + timeout_s
    chunks: list[str] = []
    while time.monotonic() < deadline:
        events = selector.select(timeout=0.5)
        if not events:
            if proc.poll() is not None:
                break
            continue
        for _key, _mask in events:
            data = proc.stdout.read(65536)
            if not data:
                continue
            text = data.decode("utf-8", errors="replace")
            log_handle.write(text)
            log_handle.flush()
            chunks.append(text)
            joined = "".join(chunks)
            if any(marker in joined for marker in markers):
                return joined
    return "".join(chunks)


def main() -> int:
    report: dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "spike_bin": str(SPIKE_BIN),
        "spike_payload": str(SPIKE_PAYLOAD),
        "status": "FAIL",
        "markers_seen": [],
        "error": None,
    }

    if not SPIKE_BIN.is_file():
        report["error"] = f"Missing spike binary: {SPIKE_BIN}"
    elif not SPIKE_PAYLOAD.is_file():
        report["error"] = f"Missing spike payload: {SPIKE_PAYLOAD}"
    else:
        with OUT_LOG.open("w", encoding="utf-8") as log_handle:
            proc = subprocess.Popen(
                [str(SPIKE_BIN), str(SPIKE_PAYLOAD)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
            selector = selectors.DefaultSelector()
            assert proc.stdout is not None
            selector.register(proc.stdout, selectors.EVENT_READ)

            try:
                boot_text = read_until(proc, selector, BOOT_MARKERS, BOOT_TIMEOUT_S, log_handle)
                seen = [marker for marker in BOOT_MARKERS if marker in boot_text]
                report["markers_seen"] = seen

                if proc.stdin is not None:
                    proc.stdin.write(b"\n")
                    proc.stdin.write(b"echo __R5_READY__\n")
                    proc.stdin.flush()
                    shell_text = read_until(proc, selector, ["__R5_READY__", PROMPT], PROMPT_TIMEOUT_S, log_handle)
                    if "__R5_READY__" in shell_text:
                        if PROMPT not in seen and PROMPT in shell_text:
                            seen.append(PROMPT)
                        report["markers_seen"] = seen

                if all(marker in report["markers_seen"] for marker in BOOT_MARKERS):
                    report["status"] = "PASS"
            except Exception as exc:
                report["error"] = str(exc)
            finally:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# R5 Guest Boot Probe",
        "",
        f"- status: `{report['status']}`",
        f"- spike_bin: `{report['spike_bin']}`",
        f"- spike_payload: `{report['spike_payload']}`",
        f"- markers_seen: `{report['markers_seen']}`",
        f"- error: `{report['error']}`",
        f"- log: `{OUT_LOG}`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
