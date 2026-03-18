#!/usr/bin/env python3
"""T13.2 - Compare HTTP Figure5 run vs TCP persistent Figure5 run."""

from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXPERIMENT_LABELS = ("gvsoc-real-delays", "baseline-no-delay-onestep")


def _latest_dir(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"Root does not exist: {root}")
    candidates = [Path(p) for p in glob.glob(str(root / "*")) if Path(p).is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No runs found in {root}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


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


def _plot(http_data: dict, tcp_data: dict, label: str, out_path: Path) -> None:
    t = http_data["t"]
    u_http = http_data["u"]
    u_tcp = tcp_data["u"]

    u1_http = [row[0] for row in u_http]
    u2_http = [row[1] for row in u_http]
    u1_tcp = [row[0] for row in u_tcp]
    u2_tcp = [row[1] for row in u_tcp]

    e1 = [abs(a - b) for a, b in zip(u1_http, u1_tcp)]
    e2 = [abs(a - b) for a, b in zip(u2_http, u2_tcp)]

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

    axes[0].plot(t, u1_http, label="http u_acc", linewidth=1.6)
    axes[0].plot(t, u1_tcp, label="tcp-persistent u_acc", linewidth=1.2, linestyle="--")
    axes[0].set_ylabel("u_acc")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    axes[1].plot(t, u2_http, label="http u_brake", linewidth=1.6)
    axes[1].plot(t, u2_tcp, label="tcp-persistent u_brake", linewidth=1.2, linestyle="--")
    axes[1].set_ylabel("u_brake")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    axes[2].plot(t, e1, label="|u_acc diff|", linewidth=1.4)
    axes[2].plot(t, e2, label="|u_brake diff|", linewidth=1.4)
    axes[2].set_xlabel("t")
    axes[2].set_ylabel("abs error")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    fig.suptitle(f"T13 HTTP vs TCP Persistent - {label}")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http-dir", type=Path, default=None)
    parser.add_argument("--tcp-persistent-dir", type=Path, default=None)
    parser.add_argument("--u-tol", type=float, default=5e-3)
    parser.add_argument("--report-json", type=Path, default=Path("artifacts/T13_tcp/http_vs_tcp_persistent.json"))
    parser.add_argument("--report-md", type=Path, default=Path("artifacts/T13_tcp/http_vs_tcp_persistent.md"))
    parser.add_argument("--plot-path", type=Path, default=Path("artifacts/T13_tcp/http_vs_tcp_persistent.png"))
    parser.add_argument("--plot-label", type=str, default="gvsoc-real-delays")
    args = parser.parse_args()

    http_dir = args.http_dir or _latest_dir(Path("/tmp/sharc_figure5"))
    tcp_dir = args.tcp_persistent_dir or _latest_dir(Path("/tmp/sharc_figure5_tcp"))

    rows = []
    failures = []

    for label in EXPERIMENT_LABELS:
        http_path = _find_json(http_dir, label)
        tcp_path = _find_json(tcp_dir, label)
        http = _load(http_path)
        tcp = _load(tcp_path)

        t_equal = http.get("t", []) == tcp.get("t", [])
        u_diff = _max_abs_diff_matrix(http.get("u", []), tcp.get("u", []))
        x_diff = _max_abs_diff_matrix(http.get("x", []), tcp.get("x", []))

        row = {
            "label": label,
            "http_path": str(http_path),
            "tcp_path": str(tcp_path),
            "n_samples": len(http.get("t", [])),
            "t_equal": t_equal,
            "u_max_abs_diff": u_diff,
            "x_max_abs_diff": x_diff,
        }
        rows.append(row)

        if not t_equal:
            failures.append(f"{label}: t vectors differ")
        if not math.isfinite(u_diff) or u_diff > args.u_tol:
            failures.append(f"{label}: u_max_abs_diff={u_diff:.6g} > {args.u_tol:.6g}")

        if label == args.plot_label:
            _plot(http, tcp, label, args.plot_path)

    report = {
        "http_dir": str(http_dir),
        "tcp_persistent_dir": str(tcp_dir),
        "u_tol": args.u_tol,
        "results": rows,
        "plot_path": str(args.plot_path),
        "pass": len(failures) == 0,
        "failures": failures,
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# T13 HTTP vs TCP Persistent",
        "",
        f"- HTTP dir: `{http_dir}`",
        f"- TCP persistent dir: `{tcp_dir}`",
        f"- Plot: `{args.plot_path}`",
        f"- PASS: `{'YES' if report['pass'] else 'NO'}`",
        "",
        "## Per Experiment",
        "",
    ]
    for row in rows:
        md.append(
            f"- `{row['label']}`: t_equal=`{row['t_equal']}`, "
            f"u_max_abs_diff=`{row['u_max_abs_diff']:.6g}`, "
            f"x_max_abs_diff=`{row['x_max_abs_diff']:.6g}`"
        )

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
