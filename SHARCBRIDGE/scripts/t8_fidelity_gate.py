#!/usr/bin/env python3
"""
T8 fidelity gate for official SHARC_RISCV pipeline.

Compares two mandatory scenario pairs:
1) ab_onestep_compare: A original vs B gvsoc
2) gvsoc_figure5: baseline-no-delay-onestep vs gvsoc-real-delays

Outputs JSON+MD reports and exits non-zero on gate failure.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THRESHOLDS = REPO_ROOT / "artifacts" / "T8_fidelity_thresholds_v1.json"
DEFAULT_JSON = REPO_ROOT / "artifacts" / "T8_fidelity_gate_latest.json"
DEFAULT_MD = REPO_ROOT / "artifacts" / "T8_fidelity_gate_latest.md"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    arr = sorted(values)
    if len(arr) == 1:
        return arr[0]
    pos = (len(arr) - 1) * (p / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return arr[lo]
    w = pos - lo
    return arr[lo] * (1.0 - w) + arr[hi] * w


def metric(vals: list[float]) -> dict[str, float]:
    absvals = [abs(v) for v in vals]
    if not vals:
        return {
            "mae": float("nan"),
            "rmse": float("nan"),
            "p95_abs": float("nan"),
            "max_abs": float("nan"),
        }
    return {
        "mae": mean(absvals),
        "rmse": math.sqrt(mean([v * v for v in vals])),
        "p95_abs": percentile(absvals, 95.0),
        "max_abs": max(absvals),
    }


def _load_sim(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def _find_one(run_dir: Path, pattern: str) -> Path:
    matches = sorted(run_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No match for pattern '{pattern}' under {run_dir}")
    return matches[0]


def _latest_run(base: Path, pattern: str) -> Path:
    runs = sorted(base.glob(pattern))
    if not runs:
        raise FileNotFoundError(f"No runs found in {base} with pattern '{pattern}'")
    return runs[-1]


def compute_pair_metrics(ref_path: Path, cand_path: Path, scenario_label: str) -> dict[str, Any]:
    ref = _load_sim(ref_path)
    cand = _load_sim(cand_path)
    n = min(
        len(ref.get("u", [])),
        len(cand.get("u", [])),
        len(ref.get("x", [])),
        len(cand.get("x", [])),
        len(ref.get("t", [])),
        len(cand.get("t", [])),
    )
    if n < 2:
        raise RuntimeError(f"Too few samples in scenario '{scenario_label}': n={n}")

    du0 = [cand["u"][i][0] - ref["u"][i][0] for i in range(n)]
    du1 = [cand["u"][i][1] - ref["u"][i][1] for i in range(n)]
    dx0 = [cand["x"][i][0] - ref["x"][i][0] for i in range(n)]
    dx1 = [cand["x"][i][1] - ref["x"][i][1] for i in range(n)]
    dx2 = [cand["x"][i][2] - ref["x"][i][2] for i in range(n)]

    return {
        "scenario": scenario_label,
        "n_samples": n,
        "ref": str(ref_path),
        "cand": str(cand_path),
        "signals": {
            "u_accel": metric(du0),
            "u_brake": metric(du1),
            "x_p": metric(dx0),
            "x_h": metric(dx1),
            "x_v": metric(dx2),
        },
    }


def compare_against_thresholds(
    metrics: dict[str, Any], limits: dict[str, Any]
) -> Tuple[bool, list[dict[str, Any]]]:
    violations: list[dict[str, Any]] = []
    signal_limits = limits.get("signals", {})

    for signal_name, sig_metrics in metrics.get("signals", {}).items():
        if signal_name not in signal_limits:
            continue
        for metric_name, limit in signal_limits[signal_name].items():
            value = sig_metrics.get(metric_name)
            if value is None:
                continue
            if value > float(limit):
                violations.append(
                    {
                        "signal": signal_name,
                        "metric": metric_name,
                        "value": value,
                        "limit": float(limit),
                    }
                )

    return len(violations) == 0, violations


def run_gate(
    ab_run_dir: Path,
    figure5_run_dir: Path,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    ab_ref = _find_one(ab_run_dir, "**/a-original-onestep/simulation_data_incremental.json")
    ab_cand = _find_one(ab_run_dir, "**/b-gvsoc-onestep/simulation_data_incremental.json")
    fg_ref = _find_one(figure5_run_dir, "**/baseline-no-delay-onestep/simulation_data_incremental.json")
    fg_cand = _find_one(figure5_run_dir, "**/gvsoc-real-delays/simulation_data_incremental.json")

    ab_metrics = compute_pair_metrics(ab_ref, ab_cand, "ab_onestep_compare")
    fg_metrics = compute_pair_metrics(fg_ref, fg_cand, "gvsoc_figure5")

    ab_ok, ab_viol = compare_against_thresholds(ab_metrics, thresholds["ab_onestep_compare"])
    fg_ok, fg_viol = compare_against_thresholds(fg_metrics, thresholds["gvsoc_figure5"])

    return {
        "pass": bool(ab_ok and fg_ok),
        "ab_onestep_compare": {
            "pass": ab_ok,
            "run_dir": str(ab_run_dir),
            "metrics": ab_metrics,
            "violations": ab_viol,
        },
        "gvsoc_figure5": {
            "pass": fg_ok,
            "run_dir": str(figure5_run_dir),
            "metrics": fg_metrics,
            "violations": fg_viol,
        },
        "thresholds": thresholds,
    }


def write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# T8 Fidelity Gate Report",
        "",
        f"- pass: `{report['pass']}`",
        "",
    ]

    for scenario in ("ab_onestep_compare", "gvsoc_figure5"):
        block = report[scenario]
        metrics = block["metrics"]
        lines += [
            f"## {scenario}",
            f"- pass: `{block['pass']}`",
            f"- run_dir: `{block['run_dir']}`",
            f"- ref: `{metrics['ref']}`",
            f"- cand: `{metrics['cand']}`",
            f"- samples: `{metrics['n_samples']}`",
            "",
            "| signal | MAE | RMSE | P95(abs) | Max(abs) |",
            "|---|---:|---:|---:|---:|",
        ]
        for signal in ("u_accel", "u_brake", "x_p", "x_h", "x_v"):
            m = metrics["signals"][signal]
            lines.append(
                f"| {signal} | {m['mae']:.6f} | {m['rmse']:.6f} | {m['p95_abs']:.6f} | {m['max_abs']:.6f} |"
            )
        if block["violations"]:
            lines += ["", "Violations:"]
            for v in block["violations"]:
                lines.append(
                    f"- `{v['signal']}.{v['metric']}` value={v['value']:.6f} > limit={v['limit']:.6f}"
                )
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run T8 fidelity gate.")
    p.add_argument("--ab-run-dir", type=Path, default=None)
    p.add_argument("--figure5-run-dir", type=Path, default=None)
    p.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    p.add_argument("--report-json", type=Path, default=DEFAULT_JSON)
    p.add_argument("--report-md", type=Path, default=DEFAULT_MD)
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if args.ab_run_dir is None:
        args.ab_run_dir = _latest_run(Path("/tmp/sharc_runs"), "*-ab_onestep_compare")
    if args.figure5_run_dir is None:
        args.figure5_run_dir = _latest_run(Path("/tmp/sharc_figure5_tcp"), "2026-*")

    with args.thresholds.open() as f:
        thresholds = json.load(f)

    report = run_gate(args.ab_run_dir, args.figure5_run_dir, thresholds)

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2) + "\n")
    write_md(report, args.report_md)

    print(json.dumps({"pass": report["pass"], "report_json": str(args.report_json)}, indent=2))
    if report["pass"]:
        print("PASS: T8 fidelity gate")
        return 0
    print("FAIL: T8 fidelity gate")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

