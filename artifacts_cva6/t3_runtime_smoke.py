#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "SHARCBRIDGE_CVA6"))

from cva6_runtime_launcher import CVA6RuntimeLauncher, SnapshotInput  # noqa: E402


ART_DIR = REPO_DIR / "artifacts_cva6"
OUT_JSON = ART_DIR / "t3_snapshot_outputs.json"
OUT_LOG = ART_DIR / "t3_runtime_smoke.log"
OUT_MD = ART_DIR / "t3_runtime_smoke.md"


def main() -> int:
    os.environ.setdefault("CVA6_RUNTIME_MODE", "spike")
    launcher = CVA6RuntimeLauncher(mode="spike")

    snap = SnapshotInput(
        request_id="t3-smoke-acc",
        k=0,
        t=0.0,
        x=[0.0, 100.0, 20.0],
        w=[22.0, 0.0],
        u_prev=[0.0, 0.0],
    )

    response = launcher.run_snapshot(snap)
    OUT_JSON.write_text(json.dumps(response, indent=2, sort_keys=True), encoding="utf-8")

    log_path = Path(response["metadata"]["log_path"])
    shutil.copyfile(log_path, OUT_LOG)

    passed = (
        response.get("status") == "SUCCESS"
        and isinstance(response.get("u"), list)
        and len(response["u"]) == 2
        and response.get("solver_status") not in {"", "ERROR"}
    )

    OUT_MD.write_text(
        "\n".join(
            [
                "# T3 Runtime Smoke",
                "",
                f"- status: `{'PASS' if passed else 'FAIL'}`",
                "- mode: `spike`",
                f"- request_id: `{response.get('request_id')}`",
                f"- control: `{response.get('u')}`",
                f"- iterations: `{response.get('iterations')}`",
                f"- cost: `{response.get('cost')}`",
                f"- solver_status: `{response.get('solver_status')}`",
                f"- runtime_log: `{OUT_LOG}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
