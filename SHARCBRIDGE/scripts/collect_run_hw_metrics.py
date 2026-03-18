#!/usr/bin/env python3
"""Collect per-experiment hardware metrics from SHARC simulation outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import fmean


EXTRA_NUMERIC_METRICS = [
    "instret",
    "cpi",
    "ipc",
    "imiss",
    "ld_stall",
    "jmp_stall",
    "stall_total",
    "branch",
    "taken_branch",
]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    s = sorted(float(v) for v in values)
    idx = int(round(0.95 * (len(s) - 1)))
    idx = max(0, min(idx, len(s) - 1))
    return float(s[idx])


def _collect_rows(run_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for sim_path in sorted(run_dir.glob("**/simulation_data_incremental.json")):
        try:
            data = json.loads(sim_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        pending = data.get("pending_computation", data.get("pending_computations", []))
        if not isinstance(pending, list):
            continue

        cycles: list[float] = []
        iters: list[float] = []
        delays_ms: list[float] = []
        extra_metrics: dict[str, list[float]] = {k: [] for k in EXTRA_NUMERIC_METRICS}
        status_counts: dict[str, int] = {}

        for item in pending:
            if not isinstance(item, dict):
                continue
            md = item.get("metadata", {})
            if not isinstance(md, dict):
                continue

            cyc = md.get("cycles")
            it = md.get("iterations")
            td = md.get("t_delay")
            st = str(md.get("status", "UNKNOWN"))
            status_counts[st] = status_counts.get(st, 0) + 1

            if isinstance(cyc, (int, float)):
                cycles.append(float(cyc))
            if isinstance(it, (int, float)):
                iters.append(float(it))
            if isinstance(td, (int, float)):
                delays_ms.append(float(td) * 1e3)
            for key in EXTRA_NUMERIC_METRICS:
                val = md.get(key)
                if isinstance(val, (int, float)):
                    extra_metrics[key].append(float(val))

        label = sim_path.parent.name
        mode = "unknown"
        low_label = label.lower()
        if "baseline" in low_label:
            mode = "baseline"
        elif "gvsoc" in low_label:
            mode = "gvsoc"
        row = {
            "mode": mode,
            "label": label,
            "source": str(sim_path),
            "n_samples": len(cycles),
            "cycles_mean": fmean(cycles) if cycles else 0.0,
            "cycles_p95": _p95(cycles),
            "cycles_max": max(cycles) if cycles else 0.0,
            "iterations_mean": fmean(iters) if iters else 0.0,
            "iterations_p95": _p95(iters),
            "iterations_max": max(iters) if iters else 0.0,
            "delay_mean_ms": fmean(delays_ms) if delays_ms else 0.0,
            "delay_p95_ms": _p95(delays_ms),
            "delay_max_ms": max(delays_ms) if delays_ms else 0.0,
            "status_counts": status_counts,
        }
        for key in EXTRA_NUMERIC_METRICS:
            values = extra_metrics[key]
            row[f"{key}_mean"] = fmean(values) if values else 0.0
            row[f"{key}_p95"] = _p95(values)
            row[f"{key}_max"] = max(values) if values else 0.0
        rows.append(row)

    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "mode",
                "label",
                "n_samples",
                "cycles_mean",
                "cycles_p95",
                "cycles_max",
                "iterations_mean",
                "iterations_p95",
                "iterations_max",
                "delay_mean_ms",
                "delay_p95_ms",
                "delay_max_ms",
                "instret_mean",
                "instret_p95",
                "instret_max",
                "cpi_mean",
                "cpi_p95",
                "cpi_max",
                "ipc_mean",
                "ipc_p95",
                "ipc_max",
                "imiss_mean",
                "imiss_p95",
                "imiss_max",
                "ld_stall_mean",
                "ld_stall_p95",
                "ld_stall_max",
                "jmp_stall_mean",
                "jmp_stall_p95",
                "jmp_stall_max",
                "stall_total_mean",
                "stall_total_p95",
                "stall_total_max",
                "branch_mean",
                "branch_p95",
                "branch_max",
                "taken_branch_mean",
                "taken_branch_p95",
                "taken_branch_max",
                "status_counts",
                "source",
            ],
        )
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["status_counts"] = json.dumps(out["status_counts"], sort_keys=True)
            writer.writerow(out)


def _write_md(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Hardware Metrics Summary",
        "",
        "| mode | label | n | cycles_mean | instret_mean | cpi_mean | ipc_mean | stall_total_mean | imiss_mean | iterations_mean | delay_mean_ms |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['mode']} | {r['label']} | {r['n_samples']} | {r['cycles_mean']:.3f} | "
            f"{r['instret_mean']:.3f} | {r['cpi_mean']:.6f} | {r['ipc_mean']:.6f} | "
            f"{r['stall_total_mean']:.3f} | {r['imiss_mean']:.3f} | "
            f"{r['iterations_mean']:.3f} | {r['delay_mean_ms']:.3f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_plot(path: Path, rows: list[dict]) -> str:
    if not rows:
        return "skip: no rows"
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        return f"skip: matplotlib unavailable ({exc})"

    labels = [r["label"] for r in rows]
    cycles = [r["cycles_mean"] for r in rows]
    delays = [r["delay_mean_ms"] for r in rows]

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].bar(labels, cycles, color="#1f77b4")
    axes[0].set_ylabel("cycles_mean")
    axes[0].grid(True, alpha=0.3, axis="y")

    axes[1].bar(labels, delays, color="#ff7f0e")
    axes[1].set_ylabel("delay_mean_ms")
    axes[1].grid(True, alpha=0.3, axis="y")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle("Figure 5 - Hardware Metrics")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="Run output directory")
    parser.add_argument("--out-prefix", type=Path, default=None, help="Output prefix without extension")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    out_prefix = args.out_prefix
    if out_prefix is None:
        out_prefix = run_dir / "latest" / "hw_metrics"

    rows = _collect_rows(run_dir)
    if not rows:
        print(f"ERROR: no simulation_data_incremental.json with hardware metadata under {run_dir}")
        return 1

    out_json = out_prefix.with_suffix(".json")
    out_csv = out_prefix.with_suffix(".csv")
    out_md = out_prefix.with_suffix(".md")
    out_plot = out_prefix.with_suffix(".png")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"run_dir": str(run_dir), "rows": rows}, indent=2), encoding="utf-8")
    _write_csv(out_csv, rows)
    _write_md(out_md, rows)
    plot_status = _write_plot(out_plot, rows)

    print(f"Rows: {len(rows)}")
    print(f"JSON: {out_json}")
    print(f"CSV:  {out_csv}")
    print(f"MD:   {out_md}")
    if plot_status == "ok":
        print(f"PLOT: {out_plot}")
    else:
        print(f"PLOT: {plot_status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
