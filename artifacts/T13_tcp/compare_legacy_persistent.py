#!/usr/bin/env python3
"""T13.1 - Compare legacy TCP Figure5 run vs persistent TCP Figure5 run."""

from __future__ import annotations

import argparse
import glob
import json
import math
import re
from pathlib import Path

import matplotlib

# Avoid permission issues in sandboxed/home-restricted environments.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXPERIMENT_LABELS = ("gvsoc-real-delays", "baseline-no-delay-onestep")


def _find_json(run_dir: Path, label: str) -> Path:
    pattern = str(run_dir / "**" / label / "simulation_data_incremental.json")
    matches = sorted(glob.glob(pattern, recursive=True))
    if not matches:
        raise FileNotFoundError(f"Missing simulation_data_incremental.json for '{label}' under {run_dir}")
    return Path(matches[0])


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _max_abs_diff_matrix(a: list, b: list) -> float:
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} != {len(b)}")
    out = 0.0
    for ra, rb in zip(a, b):
        if isinstance(ra, list) and isinstance(rb, list):
            if len(ra) != len(rb):
                raise ValueError(f"Nested length mismatch: {len(ra)} != {len(rb)}")
            for va, vb in zip(ra, rb):
                out = max(out, abs(float(va) - float(vb)))
        else:
            out = max(out, abs(float(ra) - float(rb)))
    return out


def _parse_server_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rx = re.compile(
        r"k=(?P<k>\d+) .*?cost=(?P<cost>[-+0-9.eE]+) .*?status=(?P<status>[A-Z_]+) "
        r"iters=(?P<iters>\d+)"
    )
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = rx.search(line)
        if not m:
            continue
        rows.append(
            {
                "k": int(m.group("k")),
                "cost": float(m.group("cost")),
                "status": m.group("status"),
                "iters": int(m.group("iters")),
            }
        )
    return rows


def _compare_log_sequences(legacy_rows: list[dict], persistent_rows: list[dict]) -> dict:
    if not legacy_rows or not persistent_rows:
        return {
            "n": 0,
            "cost_max_abs_diff": None,
            "iter_max_abs_diff": None,
            "status_match_ratio": None,
            "notes": "missing log rows; cost/iter/status gate skipped",
        }

    n = min(len(legacy_rows), len(persistent_rows))
    cost_max = 0.0
    iter_max = 0
    status_match = 0
    for i in range(n):
        cost_max = max(cost_max, abs(legacy_rows[i]["cost"] - persistent_rows[i]["cost"]))
        iter_max = max(iter_max, abs(legacy_rows[i]["iters"] - persistent_rows[i]["iters"]))
        if legacy_rows[i]["status"] == persistent_rows[i]["status"]:
            status_match += 1

    return {
        "n": n,
        "cost_max_abs_diff": cost_max,
        "iter_max_abs_diff": iter_max,
        "status_match_ratio": status_match / n,
        "notes": None,
    }


def _build_plot(
    legacy_data: dict,
    persistent_data: dict,
    label: str,
    out_path: Path,
) -> None:
    t = legacy_data["t"]
    u_leg = legacy_data["u"]
    u_per = persistent_data["u"]

    u1_leg = [row[0] for row in u_leg]
    u2_leg = [row[1] for row in u_leg]
    u1_per = [row[0] for row in u_per]
    u2_per = [row[1] for row in u_per]

    e1 = [abs(a - b) for a, b in zip(u1_leg, u1_per)]
    e2 = [abs(a - b) for a, b in zip(u2_leg, u2_per)]

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

    axes[0].plot(t, u1_leg, label="legacy u_acc", linewidth=1.6)
    axes[0].plot(t, u1_per, label="persistent u_acc", linewidth=1.2, linestyle="--")
    axes[0].set_ylabel("u_acc")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    axes[1].plot(t, u2_leg, label="legacy u_brake", linewidth=1.6)
    axes[1].plot(t, u2_per, label="persistent u_brake", linewidth=1.2, linestyle="--")
    axes[1].set_ylabel("u_brake")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    axes[2].plot(t, e1, label="|u_acc diff|", linewidth=1.4)
    axes[2].plot(t, e2, label="|u_brake diff|", linewidth=1.4)
    axes[2].set_xlabel("t")
    axes[2].set_ylabel("abs error")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    fig.suptitle(f"T13 Legacy vs Persistent - {label}")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-dir", type=Path, required=True)
    parser.add_argument("--persistent-dir", type=Path, required=True)
    parser.add_argument("--legacy-log", type=Path, default=Path("artifacts/T13_tcp/t13_legacy_server.log"))
    parser.add_argument("--persistent-log", type=Path, default=Path("artifacts/T13_tcp/t13_persistent_server.log"))
    parser.add_argument("--u-tol", type=float, default=5e-3)
    parser.add_argument("--cost-tol", type=float, default=5e-2)
    parser.add_argument("--iter-tol", type=int, default=1)
    parser.add_argument("--status-match-min", type=float, default=1.0)
    parser.add_argument("--report-json", type=Path, default=Path("artifacts/T13_tcp/equivalence_gate.json"))
    parser.add_argument("--report-md", type=Path, default=Path("artifacts/T13_tcp/equivalence_gate.md"))
    parser.add_argument(
        "--plot-path",
        type=Path,
        default=Path("artifacts/T13_tcp/equivalence_legacy_vs_persistent.png"),
    )
    parser.add_argument("--plot-label", type=str, default="gvsoc-real-delays")
    args = parser.parse_args()

    results = []
    failures = []

    for label in EXPERIMENT_LABELS:
        legacy_path = _find_json(args.legacy_dir, label)
        persistent_path = _find_json(args.persistent_dir, label)

        legacy = _load(legacy_path)
        persistent = _load(persistent_path)

        t_equal = legacy.get("t", []) == persistent.get("t", [])
        u_diff = _max_abs_diff_matrix(legacy.get("u", []), persistent.get("u", []))
        x_diff = _max_abs_diff_matrix(legacy.get("x", []), persistent.get("x", []))

        row = {
            "label": label,
            "legacy_path": str(legacy_path),
            "persistent_path": str(persistent_path),
            "n_samples": len(legacy.get("t", [])),
            "t_equal": t_equal,
            "u_max_abs_diff": u_diff,
            "x_max_abs_diff": x_diff,
        }
        results.append(row)

        if not t_equal:
            failures.append(f"{label}: t vectors differ")
        if not math.isfinite(u_diff) or u_diff > args.u_tol:
            failures.append(f"{label}: u_max_abs_diff={u_diff:.6g} > {args.u_tol:.6g}")

        if label == args.plot_label:
            _build_plot(legacy, persistent, label, args.plot_path)

    legacy_rows = _parse_server_log(args.legacy_log)
    persistent_rows = _parse_server_log(args.persistent_log)
    log_cmp = _compare_log_sequences(legacy_rows, persistent_rows)

    if log_cmp["cost_max_abs_diff"] is not None and log_cmp["cost_max_abs_diff"] > args.cost_tol:
        failures.append(
            f"log: cost_max_abs_diff={log_cmp['cost_max_abs_diff']:.6g} > {args.cost_tol:.6g}"
        )
    if log_cmp["iter_max_abs_diff"] is not None and log_cmp["iter_max_abs_diff"] > args.iter_tol:
        failures.append(f"log: iter_max_abs_diff={log_cmp['iter_max_abs_diff']} > {args.iter_tol}")
    if log_cmp["status_match_ratio"] is not None and log_cmp["status_match_ratio"] < args.status_match_min:
        failures.append(
            f"log: status_match_ratio={log_cmp['status_match_ratio']:.3f} < {args.status_match_min:.3f}"
        )

    report = {
        "legacy_dir": str(args.legacy_dir),
        "persistent_dir": str(args.persistent_dir),
        "thresholds": {
            "u_tol": args.u_tol,
            "cost_tol": args.cost_tol,
            "iter_tol": args.iter_tol,
            "status_match_min": args.status_match_min,
        },
        "results": results,
        "log_comparison": log_cmp,
        "plot_path": str(args.plot_path),
        "pass": len(failures) == 0,
        "failures": failures,
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# T13 Equivalence Gate (Legacy vs Persistent)",
        "",
        f"- Legacy dir: `{args.legacy_dir}`",
        f"- Persistent dir: `{args.persistent_dir}`",
        f"- Plot: `{args.plot_path}`",
        f"- PASS: `{'YES' if report['pass'] else 'NO'}`",
        "",
        "## Per Experiment",
        "",
    ]
    for row in results:
        md.extend(
            [
                f"- `{row['label']}`: t_equal=`{row['t_equal']}`, "
                f"u_max_abs_diff=`{row['u_max_abs_diff']:.6g}`, "
                f"x_max_abs_diff=`{row['x_max_abs_diff']:.6g}`",
            ]
        )
    md.extend(
        [
            "",
            "## Server Log Comparison",
            "",
            f"- n=`{log_cmp['n']}`",
            f"- cost_max_abs_diff=`{log_cmp['cost_max_abs_diff']}`",
            f"- iter_max_abs_diff=`{log_cmp['iter_max_abs_diff']}`",
            f"- status_match_ratio=`{log_cmp['status_match_ratio']}`",
        ]
    )
    if log_cmp.get("notes"):
        md.append(f"- notes: `{log_cmp['notes']}`")

    if failures:
        md.extend(["", "## Failures", ""])
        md.extend([f"- {item}" for item in failures])

    args.report_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"Wrote: {args.report_json}")
    print(f"Wrote: {args.report_md}")
    print(f"Wrote: {args.plot_path}")

    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
