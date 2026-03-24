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
ARTIFACTS_DIR = RECOVERY_DIR.parent
REPO_DIR = ARTIFACTS_DIR.parent
RESULTS_DIR = RECOVERY_DIR / "results"
LOGS_DIR = RECOVERY_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO_DIR / "SHARCBRIDGE_CVA6"))

from cva6_runtime_launcher import CVA6RuntimeLauncher, SnapshotInput  # noqa: E402


OUT_JSON = RESULTS_DIR / "c11_robust_staging_smoke.json"
OUT_MD = RESULTS_DIR / "c11_robust_staging_smoke.md"
OUT_LOG = LOGS_DIR / "c11_robust_staging_smoke.runtime.log"
PERSISTENT_LOG = Path("/tmp/sharcbridge_cva6_runtime/persistent_session.log")


def main() -> int:
    mode = os.environ.get("C11_RUNTIME_MODE", "spike_persistent").strip()
    report: dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": mode,
        "status": "FAIL",
        "error": None,
        "response": None,
        "runtime_log": None,
        "persistent_log": str(PERSISTENT_LOG),
    }

    snap = SnapshotInput(
        request_id="c11-robust-stage",
        k=0,
        t=0.0,
        x=[0.0, 100.0, 20.0],
        w=[22.0, 0.0],
        u_prev=[0.0, 0.0],
    )

    launcher = CVA6RuntimeLauncher(mode=mode)
    try:
        response = launcher.run_snapshot(snap)
        report["response"] = response
        report["status"] = "PASS" if response.get("status") == "SUCCESS" else "FAIL"

        log_path = Path(str(response.get("metadata", {}).get("log_path", "")))
        if log_path.is_file():
            shutil.copyfile(log_path, OUT_LOG)
            report["runtime_log"] = str(OUT_LOG)
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        try:
            launcher.close()
        except Exception:
            pass

    if PERSISTENT_LOG.is_file():
        report["persistent_log_exists"] = True
        report["persistent_log_size"] = PERSISTENT_LOG.stat().st_size
    else:
        report["persistent_log_exists"] = False
        report["persistent_log_size"] = 0

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    response = report.get("response") or {}
    metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
    lines = [
        "# C11 Robust Staging Smoke",
        "",
        f"- status: `{report['status']}`",
        f"- mode: `{mode}`",
        f"- error: `{report['error']}`",
        f"- runtime_log: `{report['runtime_log']}`",
        f"- persistent_log: `{report['persistent_log']}`",
        f"- persistent_log_exists: `{report['persistent_log_exists']}`",
        f"- persistent_log_size: `{report['persistent_log_size']}`",
    ]
    if isinstance(response, dict):
        lines.extend(
            [
                f"- response_status: `{response.get('status')}`",
                f"- solver_status: `{response.get('solver_status')}`",
                f"- control: `{response.get('u')}`",
                f"- backend_mode: `{metadata.get('backend_mode')}`",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
