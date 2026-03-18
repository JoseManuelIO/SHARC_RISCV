#!/usr/bin/env python3
"""T8.3 helper: generate architecture plot from HW metrics CSV."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")


def _read_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hw-csv",
        type=Path,
        default=Path("artifacts/C_OSQP_OFFLOAD/t8_hw_table.csv"),
    )
    parser.add_argument(
        "--out-plot",
        type=Path,
        default=Path("artifacts/C_OSQP_OFFLOAD/t8_hw_plot_from_table.png"),
    )
    args = parser.parse_args()

    rows = _read_csv(args.hw_csv)
    if not rows:
        raise ValueError(f"empty csv: {args.hw_csv}")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [f"{r['mode']}:{r['label']}" for r in rows]
    cycles = [float(r["cycles_mean"]) for r in rows]
    delays_ms = [float(r["delay_mean_ms"]) for r in rows]

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    axes[0].bar(labels, cycles, color="#1f77b4")
    axes[0].set_ylabel("cycles_mean")
    axes[0].set_yscale("log")
    axes[0].grid(True, alpha=0.3, axis="y")

    axes[1].bar(labels, delays_ms, color="#ff7f0e")
    axes[1].set_ylabel("delay_mean_ms")
    axes[1].grid(True, alpha=0.3, axis="y")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle("T8 Hardware Metrics")
    fig.tight_layout()
    args.out_plot.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out_plot, dpi=150)
    plt.close(fig)

    print(f"PASS: plot generated at {args.out_plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
