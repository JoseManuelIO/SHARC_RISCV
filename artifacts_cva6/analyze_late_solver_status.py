#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
ART_DIR = REPO_DIR / "artifacts_cva6"
SNAP_DIR = ART_DIR / "late_snapshots"
HOST_BIN = REPO_DIR / "CVA6_LINUX" / "plan_tests_librerias" / "build" / "acc_snapshot_host_fixed_interval"
CFG = REPO_DIR / "sharc_original" / "examples" / "acc_example" / "base_config.json"
RUN_JSON = ART_DIR / "t6_simulation_data_incremental.json"
OUT_JSON = ART_DIR / "t6_late_snapshot_replay_report.json"
OUT_MD = ART_DIR / "t6_late_snapshot_replay_report.md"


def extract_json(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise RuntimeError("JSON not found in host output")
    return json.loads(text[start:])


def main() -> int:
    integrated = json.loads(RUN_JSON.read_text(encoding="utf-8"))
    pcs = integrated.get("pending_computation", integrated.get("pending_computations", []))
    cva6 = json.loads((ART_DIR / "t6_late_snapshot_cva6_replay.json").read_text(encoding="utf-8"))

    compared = []
    status_ok = True
    max_u_diff = 0.0

    for idx in [17, 18, 19]:
        snap_path = SNAP_DIR / f"late_{idx}.json"
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        host_raw = subprocess.check_output([str(HOST_BIN), str(CFG), str(snap_path)], text=True)
        host = extract_json(host_raw)
        target = cva6[f"late_{idx}.json"]
        matches = [pc for pc in pcs if abs(float(pc.get("t_start", -999.0)) - float(snap["t"])) < 1e-9]
        if not matches:
            raise RuntimeError(f"No integrated match for snapshot {snap_path}")
        # Keep the last match for this t_start; in the integrated trace each control appears duplicated.
        integ_pc = matches[-1]
        integ = integ_pc["metadata"]
        integ_u = integ_pc["u"]

        row = {
            "snapshot": f"late_{idx}",
            "host_solver_status": host["metadata"]["solver_status"],
            "cva6_solver_status": int(target["solver_status"]),
            "integrated_solver_status": int(integ["solver_status"]),
            "host_iterations": host["metadata"]["iterations"],
            "cva6_iterations": target["iterations"],
            "integrated_iterations": integ["iterations"],
            "host_status": host["metadata"]["status"],
            "cva6_status": target["status"],
            "integrated_status": integ["status"],
            "u0_host": host["u"][0],
            "u0_cva6": target["u"][0],
            "u0_integrated": integ_u[0],
            "u1_host": host["u"][1],
            "u1_cva6": target["u"][1],
            "u1_integrated": integ_u[1],
        }
        row["u0_diff_host_cva6"] = abs(row["u0_host"] - row["u0_cva6"])
        row["u1_diff_host_cva6"] = abs(row["u1_host"] - row["u1_cva6"])
        row["u0_diff_cva6_integrated"] = abs(row["u0_cva6"] - row["u0_integrated"])
        row["u1_diff_cva6_integrated"] = abs(row["u1_cva6"] - row["u1_integrated"])
        max_u_diff = max(max_u_diff, row["u0_diff_cva6_integrated"], row["u1_diff_cva6_integrated"])

        row["match"] = (
            row["host_solver_status"] == row["cva6_solver_status"] == row["integrated_solver_status"]
            and row["host_iterations"] == row["cva6_iterations"] == row["integrated_iterations"]
        )
        status_ok = status_ok and row["match"]
        compared.append(row)

    report = {
        "status": "PASS" if status_ok else "FAIL",
        "meaning": {
            "-2": "OSQP_MAX_ITER_REACHED",
            "2": "OSQP_SOLVED_INACCURATE",
        },
        "compared": compared,
        "max_u_diff_cva6_integrated": max_u_diff,
        "notes": [
            "Los snapshots tardios del run SHARC se han rejugado fuera de SHARC.",
            "Si host, CVA6 standalone e integrado coinciden en solver_status e iteraciones, no es un bug de integracion.",
        ],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# T6 Late Snapshot Replay Report",
        "",
        f"- status: `{report['status']}`",
        "- status codes:",
        "  - `-2 = OSQP_MAX_ITER_REACHED`",
        "  - `2 = OSQP_SOLVED_INACCURATE`",
        f"- max |u| diff CVA6 integrated replay: `{report['max_u_diff_cva6_integrated']}`",
        "",
        "## Compared snapshots",
    ]
    for row in compared:
        lines.extend(
            [
                "",
                f"- `{row['snapshot']}`",
                f"  - statuses: `host={row['host_solver_status']}`, `cva6={row['cva6_solver_status']}`, `integrated={row['integrated_solver_status']}`",
                f"  - iterations: `host={row['host_iterations']}`, `cva6={row['cva6_iterations']}`, `integrated={row['integrated_iterations']}`",
                f"  - match: `{'PASS' if row['match'] else 'FAIL'}`",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if status_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
