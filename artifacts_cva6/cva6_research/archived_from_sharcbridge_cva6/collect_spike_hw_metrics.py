#!/usr/bin/env python3
"""Collect Figure 5 hardware and solver metrics for the CVA6/Spike backend."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import fmean


UNSUPPORTED_SPIKE_METRICS = [
    "imiss",
    "ld_stall",
    "jmp_stall",
    "stall_total",
    "branch",
    "taken_branch",
    "cache_miss",
    "cache_latency",
]

NUMERIC_FIELDS = {
    "cycles": "cycles",
    "scaled_cycles_for_delay": "scaled_cycles_for_delay",
    "instret": "instret",
    "cpi": "cpi",
    "ipc": "ipc",
    "iterations": "iterations",
    "cost": "cost",
    "constraint_error": "constraint_error",
    "dual_residual": "dual_residual",
}


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    s = sorted(float(v) for v in values)
    idx = int(round(0.95 * (len(s) - 1)))
    idx = max(0, min(idx, len(s) - 1))
    return float(s[idx])


def _mode_from_label(label: str) -> str:
    low = label.lower()
    if "baseline" in low:
        return "baseline"
    if "cva6" in low:
        return "cva6"
    return "unknown"


def _stable_counts(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in values:
        counts[item] = counts.get(item, 0) + 1
    return dict(sorted(counts.items()))


def _stringify_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "{}"
    return json.dumps(counts, sort_keys=True, separators=(",", ":"))


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

        numeric_values: dict[str, list[float]] = {key: [] for key in NUMERIC_FIELDS}
        delays_ms: list[float] = []
        statuses: list[str] = []
        solver_statuses: list[str] = []
        feasible_values: list[float] = []
        backend_modes: list[str] = []
        chip_cycle_times_ns: list[float] = []

        for item in pending:
            if not isinstance(item, dict):
                continue
            md = item.get("metadata", {})
            if not isinstance(md, dict):
                continue

            for key in NUMERIC_FIELDS:
                value = md.get(key)
                if isinstance(value, (int, float)):
                    numeric_values[key].append(float(value))

            delay_s = md.get("t_delay")
            if isinstance(delay_s, (int, float)):
                delays_ms.append(float(delay_s) * 1e3)

            statuses.append(str(md.get("status", "UNKNOWN")))
            solver_statuses.append(str(md.get("solver_status", "UNKNOWN")))

            feasible = md.get("is_feasible")
            if isinstance(feasible, bool):
                feasible_values.append(1.0 if feasible else 0.0)

            backend_mode = md.get("backend_mode")
            if backend_mode is not None:
                backend_modes.append(str(backend_mode))

            chip_cycle_ns = md.get("chip_cycle_time_ns_effective")
            if isinstance(chip_cycle_ns, (int, float)):
                chip_cycle_times_ns.append(float(chip_cycle_ns))

        label = sim_path.parent.name
        row = {
            "mode": _mode_from_label(label),
            "label": label,
            "source": str(sim_path),
            "n_samples": len(statuses),
            "delay_mean_ms": fmean(delays_ms) if delays_ms else 0.0,
            "delay_p95_ms": _p95(delays_ms),
            "delay_max_ms": max(delays_ms) if delays_ms else 0.0,
            "status_counts": _stable_counts(statuses),
            "solver_status_counts": _stable_counts(solver_statuses),
            "feasible_ratio": fmean(feasible_values) if feasible_values else 0.0,
            "backend_mode": backend_modes[0] if len(set(backend_modes)) == 1 and backend_modes else "mixed" if backend_modes else "",
            "chip_cycle_time_ns_effective": (
                chip_cycle_times_ns[0]
                if len({round(v, 12) for v in chip_cycle_times_ns}) == 1 and chip_cycle_times_ns
                else 0.0
            ),
        }

        for key in NUMERIC_FIELDS:
            values = numeric_values[key]
            row[f"{key}_mean"] = fmean(values) if values else 0.0
            row[f"{key}_p95"] = _p95(values)
            row[f"{key}_max"] = max(values) if values else 0.0

        rows.append(row)

    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "mode",
        "label",
        "backend_mode",
        "n_samples",
        "cycles_mean",
        "cycles_p95",
        "cycles_max",
        "scaled_cycles_for_delay_mean",
        "scaled_cycles_for_delay_p95",
        "scaled_cycles_for_delay_max",
        "instret_mean",
        "instret_p95",
        "instret_max",
        "cpi_mean",
        "cpi_p95",
        "cpi_max",
        "ipc_mean",
        "ipc_p95",
        "ipc_max",
        "iterations_mean",
        "iterations_p95",
        "iterations_max",
        "cost_mean",
        "cost_p95",
        "cost_max",
        "constraint_error_mean",
        "constraint_error_p95",
        "constraint_error_max",
        "dual_residual_mean",
        "dual_residual_p95",
        "dual_residual_max",
        "feasible_ratio",
        "delay_mean_ms",
        "delay_p95_ms",
        "delay_max_ms",
        "chip_cycle_time_ns_effective",
        "status_counts",
        "solver_status_counts",
        "source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["status_counts"] = _stringify_counts(row["status_counts"])
            out["solver_status_counts"] = _stringify_counts(row["solver_status_counts"])
            writer.writerow(out)


def _write_md(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Spike Hardware Metrics Summary",
        "",
        "Supported backend metrics: `cycles`, `scaled_cycles_for_delay`, `instret`, `cpi`, `ipc`, `iterations`, `cost`, `constraint_error`, `dual_residual`, `t_delay`.",
        "",
        "Unsupported or not modeled in this backend: "
        + ", ".join(f"`{metric}`" for metric in UNSUPPORTED_SPIKE_METRICS)
        + ".",
        "",
        "| mode | label | n | cycles_mean | instret_mean | cpi_mean | ipc_mean | iterations_mean | cost_mean | feasible_ratio | delay_mean_ms | solver_status_counts |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['mode']} | {row['label']} | {row['n_samples']} | "
            f"{row['cycles_mean']:.3f} | {row['instret_mean']:.3f} | {row['cpi_mean']:.6f} | "
            f"{row['ipc_mean']:.6f} | {row['iterations_mean']:.3f} | {row['cost_mean']:.6f} | "
            f"{row['feasible_ratio']:.3f} | {row['delay_mean_ms']:.3f} | "
            f"`{_stringify_counts(row['solver_status_counts'])}` |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `delay_mean_ms` is derived from `metadata.t_delay` and is host-side runtime context, not a cache/memory latency model.",
            "- The plant delay used by SHARC continues to come from `gvsoc_cycles_<k>.txt` via `scaled_cycles_for_delay`.",
            "",
        ]
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

    labels = [row["label"] for row in rows]
    cycles = [row["cycles_mean"] for row in rows]
    instret = [row["instret_mean"] for row in rows]
    delays = [row["delay_mean_ms"] for row in rows]

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    axes[0].bar(labels, cycles, color="#1f77b4")
    axes[0].set_ylabel("cycles_mean")
    axes[0].grid(True, alpha=0.3, axis="y")

    axes[1].bar(labels, instret, color="#2ca02c")
    axes[1].set_ylabel("instret_mean")
    axes[1].grid(True, alpha=0.3, axis="y")

    axes[2].bar(labels, delays, color="#ff7f0e")
    axes[2].set_ylabel("delay_mean_ms")
    axes[2].grid(True, alpha=0.3, axis="y")
    axes[2].tick_params(axis="x", rotation=20)

    fig.suptitle("Figure 5 - CVA6/Spike Metrics")
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
    out_prefix = args.out_prefix or (run_dir / "latest" / "hw_metrics_spike")

    rows = _collect_rows(run_dir)
    if not rows:
        print(f"ERROR: no simulation_data_incremental.json with Spike metadata under {run_dir}")
        return 1

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    out_json = out_prefix.with_suffix(".json")
    out_csv = out_prefix.with_suffix(".csv")
    out_md = out_prefix.with_suffix(".md")
    out_plot = out_prefix.with_suffix(".png")

    payload = {
        "backend": "cva6_spike",
        "run_dir": str(run_dir),
        "unsupported_metrics": UNSUPPORTED_SPIKE_METRICS,
        "rows": rows,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
