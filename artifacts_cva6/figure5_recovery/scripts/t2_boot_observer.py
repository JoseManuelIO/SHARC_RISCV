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

OUT_LOG = LOGS_DIR / "t2_boot_observer.log"
OUT_JSON = RESULTS_DIR / "t2_boot_observer.json"
OUT_MD = RESULTS_DIR / "t2_boot_observer.md"

SDK_DIR = Path(os.environ.get("CVA6_SDK_DIR", REPO_DIR / "CVA6_LINUX" / "cva6-sdk"))
SPIKE_BIN = Path(os.environ.get("CVA6_SPIKE_BIN", SDK_DIR / "install64" / "bin" / "spike"))
SPIKE_PAYLOAD = Path(os.environ.get("CVA6_SPIKE_PAYLOAD", SDK_DIR / "install64" / "spike_fw_payload.elf"))
OBSERVE_TIMEOUT_S = float(os.environ.get("T2_BOOT_OBSERVE_TIMEOUT_S", "120"))
IDLE_TIMEOUT_S = float(os.environ.get("T2_BOOT_IDLE_TIMEOUT_S", "20"))
POKE_ON_IDLE = os.environ.get("T2_BOOT_POKE_ON_IDLE", "1").strip().lower() in {"1", "true", "yes", "on"}
INTERRUPT_ON_IDLE = os.environ.get("T2_BOOT_INTERRUPT_ON_IDLE", "0").strip().lower() in {"1", "true", "yes", "on"}

MARKERS = [
    "Run /init as init process",
    "Starting syslogd: OK",
    "Starting klogd: OK",
    "Running sysctl: OK",
    "Starting rpcbind: OK",
    "Starting sshd: OK",
    "NFS preparation skipped, OK",
    "# ",
]


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
    seen_markers: list[str] = []
    last_output_ts = time.time()
    poked = False
    interrupted = False
    error: str | None = None

    try:
        if proc.stdout is None:
            raise RuntimeError("Failed to open Spike stdout")
        selector.register(proc.stdout, selectors.EVENT_READ)

        deadline = time.time() + OBSERVE_TIMEOUT_S
        while time.time() < deadline:
            events = selector.select(timeout=0.2)
            if not events:
                if proc.poll() is not None:
                    break
                if time.time() - last_output_ts > IDLE_TIMEOUT_S:
                    if INTERRUPT_ON_IDLE and not interrupted and proc.stdin is not None:
                        proc.stdin.write(b"\x03")
                        proc.stdin.flush()
                        interrupted = True
                        last_output_ts = time.time()
                        continue
                    if POKE_ON_IDLE and not poked and proc.stdin is not None:
                        proc.stdin.write(b"\n")
                        proc.stdin.flush()
                        poked = True
                        last_output_ts = time.time()
                        continue
                    break
                continue
            for key, _ in events:
                chunk = key.fileobj.read(4096)
                if not chunk:
                    if proc.poll() is not None:
                        break
                    continue
                text = chunk.decode("utf-8", errors="ignore")
                chunks.append(text)
                last_output_ts = time.time()
                joined = "".join(chunks)
                for marker in MARKERS:
                    if marker in joined and marker not in seen_markers:
                        seen_markers.append(marker)
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

    joined = "".join(chunks)
    reached_prompt = "# " in joined
    reached_ready = any(m in joined for m in ("Starting sshd: OK", "NFS preparation skipped, OK", "# "))
    classification = "boot_ready" if reached_ready else "boot_partial"
    if error is not None:
        classification = "boot_probe_failed"

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "spike_bin": str(SPIKE_BIN),
        "spike_payload": str(SPIKE_PAYLOAD),
        "log_path": str(OUT_LOG),
        "observe_timeout_s": OBSERVE_TIMEOUT_S,
        "idle_timeout_s": IDLE_TIMEOUT_S,
        "poke_on_idle": POKE_ON_IDLE,
        "interrupt_on_idle": INTERRUPT_ON_IDLE,
        "poked": poked,
        "interrupted": interrupted,
        "seen_markers": seen_markers,
        "reached_prompt": reached_prompt,
        "reached_ready": reached_ready,
        "classification": classification,
        "error": error,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# T2 Boot Observer",
                "",
                f"- classification: `{classification}`",
                f"- reached_prompt: `{reached_prompt}`",
                f"- reached_ready: `{reached_ready}`",
                f"- seen_markers: `{seen_markers}`",
                f"- log_path: `{OUT_LOG}`",
                f"- interrupted: `{interrupted}`",
                f"- error: `{error}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if reached_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
