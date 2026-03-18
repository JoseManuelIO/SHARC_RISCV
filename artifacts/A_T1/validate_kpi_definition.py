#!/usr/bin/env python3
import json
import sys
from pathlib import Path


REQUIRED_TOP_KEYS = ["version", "scope", "signals", "kpis", "brake_segments"]
REQUIRED_KPI_IDS = {
    "rmse_u_accel",
    "rmse_u_brake",
    "mae_u_accel",
    "mae_u_brake",
    "max_abs_u_accel",
    "max_abs_u_brake",
    "rmse_x_p",
    "rmse_x_h",
    "rmse_x_v",
    "max_abs_x_h",
    "solver_status_match_ratio",
    "timeout_count_candidate",
    "invalid_step_count_candidate",
    "cycles_mean",
    "cycles_p95",
    "delay_mean_s",
    "delay_p95_s",
}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/A_T1/kpi_definition.json")
    data = json.loads(path.read_text())

    missing_top = [k for k in REQUIRED_TOP_KEYS if k not in data]
    if missing_top:
        print(f"FAIL: missing top-level keys: {missing_top}")
        return 1

    if not isinstance(data["kpis"], list) or len(data["kpis"]) == 0:
        print("FAIL: kpis must be a non-empty list")
        return 1

    ids = set()
    for idx, kpi in enumerate(data["kpis"]):
        for key in ("id", "group", "formula", "unit"):
            if key not in kpi:
                print(f"FAIL: KPI[{idx}] missing key '{key}'")
                return 1
            if not str(kpi[key]).strip():
                print(f"FAIL: KPI[{idx}] key '{key}' is empty")
                return 1
        ids.add(kpi["id"])

    missing_ids = sorted(REQUIRED_KPI_IDS - ids)
    if missing_ids:
        print(f"FAIL: missing required KPI ids: {missing_ids}")
        return 1

    if not isinstance(data["brake_segments"], list) or len(data["brake_segments"]) < 2:
        print("FAIL: brake_segments must contain at least 2 segments")
        return 1

    print("PASS: KPI definition is valid and complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
