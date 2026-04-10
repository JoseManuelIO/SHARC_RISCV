#!/usr/bin/env python3
"""Publish a Figure-5-style cache comparison bundle into cache_sweep/latest."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache-sweep")

import matplotlib.pyplot as plt
import numpy as np


PREFERRED_CASES = [
    ("cache_1mb", "Baseline (1 MB)"),
    ("cache_262kb", "262 KB"),
    ("cache_32kb", "32 KB"),
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_sim_and_config(out_dir: Path, experiment: str) -> tuple[Path, Path]:
    sim_candidates = sorted(out_dir.glob(f"**/{experiment}/simulation_data_incremental.json"))
    if not sim_candidates:
        raise FileNotFoundError(f"missing {experiment}/simulation_data_incremental.json under {out_dir}")
    sim_path = sim_candidates[0]
    cfg_path = sim_path.parent / "config.json"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"missing config.json next to {sim_path}")
    return sim_path, cfg_path


def _build_experiment_entry(run: dict, public_label: str, experiment: str, latest_dir: Path) -> dict:
    out_dir = Path(run["out_dir"])
    sim_path, cfg_path = _find_sim_and_config(out_dir, experiment)
    sim = _load_json(sim_path)
    cfg = _load_json(cfg_path)
    cfg["label"] = public_label
    cfg["experiment_label"] = public_label
    exp_data = {k: sim.get(k, []) for k in ("k", "t", "x", "u", "w")}
    exp_data["pending_computations"] = sim.get("pending_computation", sim.get("pending_computations", []))
    exp_data["batches"] = sim.get("batches", None)
    return {
        "label": public_label,
        "experiment directory": str(latest_dir),
        "experiment data": exp_data,
        "experiment config": cfg,
    }


def _iter_unique_pending_computations(pending_computations: Iterable[dict | None]) -> list[dict]:
    unique = []
    seen = set()
    for pc in pending_computations:
        if not isinstance(pc, dict):
            continue
        key = (
            round(float(pc.get("t_start", 0.0)), 9),
            round(float(pc.get("delay", 0.0)), 9),
            round(float(pc.get("metadata", {}).get("t_delay", 0.0)), 9),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(pc)
    return unique


def _delay_value_for_plot(pc: dict, delay_source: str) -> float | None:
    if delay_source == "t_delay":
        value = pc.get("metadata", {}).get("t_delay")
    else:
        value = pc.get("delay")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def plot_experiment_result(
    result_data,
    velocity_ax,
    headway_ax,
    delay_ax,
    control_ax,
    color,
    delay_source: str,
):
    t = np.array(result_data["t"])
    u = np.array(result_data["u"])
    x = np.array(result_data["x"])
    h = x[:, 1]
    v = x[:, 2]

    velocity_ax.plot(t, v, label=None, c=color)
    headway_ax.plot(t, h, label=None, c=color)

    pc_t, pc_delay = [], []
    for pc in _iter_unique_pending_computations(result_data["pending_computations"]):
        t_start = float(pc["t_start"])
        delay = _delay_value_for_plot(pc, delay_source)
        if delay is None:
            continue
        pc_t.extend([t_start, t_start + delay, np.nan])
        pc_delay.extend([delay, delay, np.nan])
    delay_ax.plot(pc_t, pc_delay, color=color)

    control_ax.plot(t, u[:, 0], color=color, linestyle='-')
    control_ax.plot(t, u[:, 1], color=color, linestyle=':')

    if result_data["batches"] is not None:
        for batch in result_data["batches"]:
            start_time = batch["valid_simulation_data"]["t"][0]
            idx = np.where(t == start_time)[0][0]
            velocity_ax.plot(t[idx], v[idx], 'kx', markersize=4)
            headway_ax.plot(t[idx], h[idx], 'kx', markersize=4)


def plot_experiment_list(experiment_list, delay_source: str):
    colors = iter(plt.cm.tab10.colors)
    n_axs = 4
    fig, axs = plt.subplots(n_axs, 1, figsize=(10, 13), sharex=True)
    plts_for_bottom_legend = []
    velocity_ax = axs[0]
    headway_ax = axs[1]
    delay_ax = axs[2]
    control_ax = axs[3]

    for experiment in experiment_list:
        label = experiment[0]
        result = experiment[1]
        result_data = result["experiment data"]
        color = next(colors)
        plot_experiment_result(
            result_data,
            velocity_ax=velocity_ax,
            headway_ax=headway_ax,
            delay_ax=delay_ax,
            control_ax=control_ax,
            color=color,
            delay_source=delay_source,
        )
        line = velocity_ax.plot(np.nan, np.nan, c=color)[0]
        plts_for_bottom_legend.append((line, label))

    result = experiment_list[-1][1]
    result_data = result["experiment data"]
    sample_time = result["experiment config"]["system_parameters"]["sample_time"]
    d_min = result["experiment config"]["system_parameters"]["d_min"]
    w = np.array(result_data["w"])
    v_front = w[:, 0]
    t = np.array(result_data["t"])

    velocity_ax.plot(t, v_front, label="Front Velocity", color="black")
    if delay_source == "pending_delay":
        delay_ax.axhline(y=sample_time, color="black", linestyle="--", linewidth=2, label=f"Sample Time ({sample_time} s)")
    headway_ax.axhline(y=d_min, color="black", linestyle="--", linewidth=2, label="Minimum Headway $d_{min}$")
    control_ax.plot(np.nan, np.nan, label="Acceleration Force", color="black", linestyle="-")
    control_ax.plot(np.nan, np.nan, label="Braking Force", color="black", linestyle=":")
    batch_start_markers = velocity_ax.plot(np.nan, np.nan, "kx", markersize=4)[0]
    plts_for_bottom_legend.append((batch_start_markers, "Batch start"))

    xlim = (0, result_data["t"][-1])
    velocity_ax.set(ylabel="Velocity $v$ [m/s]", title="Velocity", xlim=xlim, ylim=(0, None))
    velocity_ax.grid(True)
    velocity_ax.legend()

    headway_ax.set(ylabel="Headway $h$ [m]", title="Headway", xlim=xlim, ylim=(0, None))
    headway_ax.grid(True)
    headway_ax.legend()

    if delay_source == "t_delay":
        delay_ax.set(
            ylabel="Snapshot MPC Solve Time $t_{delay}$ [s]",
            title="Delays (RISC-V MPC Solve Time, log scale)",
            xlim=xlim,
        )
        delay_ax.set_yscale("log")
    else:
        delay_ax.set(ylabel="Delay $\\tau$ [s]", title="Delays", xlim=xlim)
    delay_ax.grid(True)
    handles, labels = delay_ax.get_legend_handles_labels()
    if handles:
        delay_ax.legend()

    control_ax.set(xlabel="Time [s]", ylabel="Control Input $u$ [N]", title="Control", xlim=xlim)
    control_ax.grid(True)
    control_ax.legend()

    fig.legend(
        *zip(*plts_for_bottom_legend),
        loc="lower center",
        bbox_to_anchor=(0.55, 0.12),
        ncol=4,
        columnspacing=1.0,
        handlelength=1.5,
        handletextpad=0.5,
        bbox_transform=fig.transFigure,
        borderaxespad=0.2,
    )
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.23)
    return plt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts_cva6/cache_sweep/results/cache_sweep_manifest.json"),
    )
    parser.add_argument(
        "--latest-dir",
        type=Path,
        default=Path("artifacts_cva6/cache_sweep/latest"),
    )
    parser.add_argument(
        "--experiment",
        default="cva6-real-delays",
    )
    parser.add_argument(
        "--delay-source",
        choices=("pending_delay", "t_delay"),
        default="t_delay",
        help="Delay signal to draw in the Delays panel.",
    )
    args = parser.parse_args()

    manifest = _load_json(args.manifest.resolve())
    runs_by_id = {run["id"]: run for run in manifest.get("runs", [])}
    latest_dir = args.latest_dir.resolve()
    latest_dir.mkdir(parents=True, exist_ok=True)

    data = {}
    plotted = []
    for case_id, public_label in PREFERRED_CASES:
        run = runs_by_id.get(case_id)
        if run is None:
            continue
        entry = _build_experiment_entry(run, public_label, args.experiment, latest_dir)
        data[case_id] = entry
        plotted.append((public_label, entry))

    if not plotted:
        raise SystemExit("ERROR: no cache runs available to publish")

    bundle_path = latest_dir / "experiment_list_data_incremental.json"
    bundle_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    plt_obj = plot_experiment_list(plotted, delay_source=args.delay_source)
    plot_path = latest_dir / "plot_cache.png"
    plt_obj.savefig(plot_path)
    plt.close(plt_obj.gcf())

    report = {
        "status": "PASS",
        "manifest": str(args.manifest.resolve()),
        "latest_dir": str(latest_dir),
        "plot_cache_png": str(plot_path),
        "experiment_bundle": str(bundle_path),
        "plotted_labels": [label for label, _ in plotted],
        "experiment": args.experiment,
        "delay_source": args.delay_source,
    }
    report_path = latest_dir / "cache_latest_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"latest_dir={latest_dir}")
    print(f"bundle={bundle_path}")
    print(f"plot_cache={plot_path}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
