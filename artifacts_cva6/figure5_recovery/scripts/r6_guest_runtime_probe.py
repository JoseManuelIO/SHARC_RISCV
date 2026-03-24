#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RECOVERY_DIR = SCRIPT_DIR.parent
REPO_DIR = RECOVERY_DIR.parent.parent
RESULTS_DIR = RECOVERY_DIR / "results"
LOGS_DIR = RECOVERY_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LABEL = os.environ.get("R6_LABEL", "r6_guest_runtime_probe").strip() or "r6_guest_runtime_probe"
OUT_JSON = RESULTS_DIR / f"{LABEL}.json"
OUT_MD = RESULTS_DIR / f"{LABEL}.md"
OUT_LOG = LOGS_DIR / f"{LABEL}.runtime.log"

os.environ.setdefault("CVA6_RUNTIME_MODE", os.environ.get("R6_RUNTIME_MODE", "spike"))

sys.path.insert(0, str(REPO_DIR / "SHARCBRIDGE_CVA6"))

from cva6_runtime_launcher import CVA6RuntimeLauncher, SnapshotInput  # noqa: E402


def main() -> int:
    mode = os.environ.get("R6_RUNTIME_MODE", os.environ.get("CVA6_RUNTIME_MODE", "spike")).strip()
    report: dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": mode,
        "status": "FAIL",
        "classification": "runtime_missing_or_failed",
        "error": None,
        "response": None,
        "runtime_log": None,
    }

    launcher = CVA6RuntimeLauncher(mode=mode)
    snap = SnapshotInput(
        request_id="r6-runtime-probe",
        k=0,
        t=0.0,
        x=[0.0, 100.0, 20.0],
        w=[22.0, 0.0],
        u_prev=[0.0, 0.0],
    )

    try:
        response = launcher.run_snapshot(snap)
        report["response"] = response
        log_path = Path(str(response.get("metadata", {}).get("log_path", "")))
        if log_path.is_file():
            shutil.copyfile(log_path, OUT_LOG)
            report["runtime_log"] = str(OUT_LOG)

        if response.get("status") == "SUCCESS":
            report["status"] = "PASS"
            report["classification"] = "runtime_present_and_executable"
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        try:
            launcher.close()
        except Exception:
            pass

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    response = report.get("response") or {}
    metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
    lines = [
        "# R6 Guest Runtime Probe",
        "",
        f"- status: `{report['status']}`",
        f"- classification: `{report['classification']}`",
        f"- mode: `{mode}`",
        f"- error: `{report['error']}`",
        f"- runtime_log: `{report['runtime_log']}`",
    ]
    if isinstance(response, dict):
        lines.extend(
            [
                f"- response_status: `{response.get('status')}`",
                f"- solver_status: `{response.get('solver_status')}`",
                f"- control: `{response.get('u')}`",
                f"- backend_mode: `{metadata.get('backend_mode')}`",
                f"- log_path: `{metadata.get('log_path')}`",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
