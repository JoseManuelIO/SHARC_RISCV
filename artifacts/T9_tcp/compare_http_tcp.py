#!/usr/bin/env python3
"""Compare Figure 5 outputs produced by HTTP vs TCP transport."""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HTTP_ROOT = Path("/tmp/sharc_figure5")
DEFAULT_TCP_ROOT = Path("/tmp/sharc_figure5_tcp")
DEFAULT_U_TOL = 5e-3
DEFAULT_COST_TOL = 5e-2
EXPERIMENT_LABELS = ("gvsoc-real-delays", "baseline-no-delay-onestep")


@dataclass
class ComparisonResult:
    label: str
    n_samples: int
    t_equal: bool
    u_max_abs_diff: float
    cost_max_abs_diff: float | None
    x_max_abs_diff: float


def _latest_dir(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"Root directory does not exist: {root}")
    candidates = [Path(p) for p in glob.glob(str(root / "*")) if Path(p).is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No runs found under {root}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _find_experiment_json(run_dir: Path, label: str) -> Path:
    pattern = str(run_dir / "**" / label / "simulation_data_incremental.json")
    matches = sorted(glob.glob(pattern, recursive=True))
    if not matches:
        raise FileNotFoundError(f"Missing simulation_data_incremental.json for '{label}' under {run_dir}")
    return Path(matches[0])


def _max_abs_diff_matrix(a: list, b: list) -> float:
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} != {len(b)}")
    max_diff = 0.0
    for row_a, row_b in zip(a, b):
        if isinstance(row_a, list) and isinstance(row_b, list):
            if len(row_a) != len(row_b):
                raise ValueError(f"Nested length mismatch: {len(row_a)} != {len(row_b)}")
            for va, vb in zip(row_a, row_b):
                max_diff = max(max_diff, abs(float(va) - float(vb)))
        else:
            max_diff = max(max_diff, abs(float(row_a) - float(row_b)))
    return max_diff


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def compare_runs(http_dir: Path, tcp_dir: Path) -> tuple[list[ComparisonResult], list[str]]:
    results: list[ComparisonResult] = []
    notes: list[str] = []

    for label in EXPERIMENT_LABELS:
        http_path = _find_experiment_json(http_dir, label)
        tcp_path = _find_experiment_json(tcp_dir, label)

        http = _load_json(http_path)
        tcp = _load_json(tcp_path)

        t_http = http.get("t", [])
        t_tcp = tcp.get("t", [])
        u_http = http.get("u", [])
        u_tcp = tcp.get("u", [])
        x_http = http.get("x", [])
        x_tcp = tcp.get("x", [])

        if not (len(t_http) == len(t_tcp) == len(u_http) == len(u_tcp) == len(x_http) == len(x_tcp)):
            raise ValueError(
                f"Inconsistent sample lengths for {label}: "
                f"t=({len(t_http)},{len(t_tcp)}), "
                f"u=({len(u_http)},{len(u_tcp)}), "
                f"x=({len(x_http)},{len(x_tcp)})"
            )

        t_equal = t_http == t_tcp
        u_diff = _max_abs_diff_matrix(u_http, u_tcp)
        x_diff = _max_abs_diff_matrix(x_http, x_tcp)

        cost_diff: float | None = None
        if "cost" in http and "cost" in tcp:
            cost_diff = _max_abs_diff_matrix(http["cost"], tcp["cost"])
        else:
            notes.append(f"{label}: cost not present in simulation_data_incremental.json; cost gate skipped")

        results.append(
            ComparisonResult(
                label=label,
                n_samples=len(t_http),
                t_equal=t_equal,
                u_max_abs_diff=u_diff,
                cost_max_abs_diff=cost_diff,
                x_max_abs_diff=x_diff,
            )
        )

    return results, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http-dir", type=Path, default=None, help="HTTP run directory (defaults to latest /tmp/sharc_figure5/*)")
    parser.add_argument("--tcp-dir", type=Path, default=None, help="TCP run directory (defaults to latest /tmp/sharc_figure5_tcp/*)")
    parser.add_argument("--u-tol", type=float, default=DEFAULT_U_TOL, help="Max abs tolerance for u")
    parser.add_argument("--cost-tol", type=float, default=DEFAULT_COST_TOL, help="Max abs tolerance for cost")
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("artifacts/T9_tcp/http_tcp_equivalence_latest.json"),
        help="Path to write JSON report",
    )
    args = parser.parse_args()

    http_dir = args.http_dir or _latest_dir(DEFAULT_HTTP_ROOT)
    tcp_dir = args.tcp_dir or _latest_dir(DEFAULT_TCP_ROOT)

    results, notes = compare_runs(http_dir=http_dir, tcp_dir=tcp_dir)

    failures: list[str] = []
    for res in results:
        if not res.t_equal:
            failures.append(f"{res.label}: t vectors differ")
        if not math.isfinite(res.u_max_abs_diff) or res.u_max_abs_diff > args.u_tol:
            failures.append(f"{res.label}: u_max_abs_diff={res.u_max_abs_diff:.6g} > {args.u_tol:.6g}")
        if res.cost_max_abs_diff is not None:
            if (not math.isfinite(res.cost_max_abs_diff)) or (res.cost_max_abs_diff > args.cost_tol):
                failures.append(
                    f"{res.label}: cost_max_abs_diff={res.cost_max_abs_diff:.6g} > {args.cost_tol:.6g}"
                )

    report = {
        "http_dir": str(http_dir),
        "tcp_dir": str(tcp_dir),
        "u_tol": args.u_tol,
        "cost_tol": args.cost_tol,
        "results": [
            {
                "label": r.label,
                "n_samples": r.n_samples,
                "t_equal": r.t_equal,
                "u_max_abs_diff": r.u_max_abs_diff,
                "x_max_abs_diff": r.x_max_abs_diff,
                "cost_max_abs_diff": r.cost_max_abs_diff,
            }
            for r in results
        ],
        "notes": notes,
        "pass": len(failures) == 0,
        "failures": failures,
    }

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    with args.report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"HTTP dir: {http_dir}")
    print(f"TCP dir:  {tcp_dir}")
    for item in report["results"]:
        print(
            f"[{item['label']}] n={item['n_samples']} t_equal={item['t_equal']} "
            f"u_max={item['u_max_abs_diff']:.6g} x_max={item['x_max_abs_diff']:.6g} "
            f"cost_max={item['cost_max_abs_diff']}"
        )
    for note in notes:
        print(f"NOTE: {note}")

    print(f"Report: {args.report_path}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print("PASS: HTTP vs TCP equivalence within configured tolerances")
    return 0


if __name__ == "__main__":
    sys.exit(main())
