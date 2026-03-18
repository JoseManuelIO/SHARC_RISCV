#!/usr/bin/env python3
import json
import math
from pathlib import Path
from statistics import mean


DATASET = Path("artifacts/A_T2/ab_dataset.jsonl")
OUT_MD = Path("artifacts/A_T2/ab_step_report.md")


def percentile(values, p):
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


def rmse(vals):
    return math.sqrt(mean([v * v for v in vals])) if vals else float("nan")


def segment_name(t):
    if t < 2.0:
        return "early_0_2s"
    if t < 5.0:
        return "mid_2_5s"
    if t < 6.5:
        return "transition_5_6_5s"
    return "late_6_5_8s"


def metric_block(vals):
    return {
        "mean_abs": mean([abs(v) for v in vals]),
        "p95_abs": percentile([abs(v) for v in vals], 95),
        "max_abs": max([abs(v) for v in vals]),
        "rmse": rmse(vals),
    }


def main():
    rows = [json.loads(ln) for ln in DATASET.read_text().splitlines() if ln.strip()]
    if not rows:
        raise SystemExit("No dataset rows")

    du0 = [r["u_candidate"][0] - r["u_ref"][0] for r in rows]
    du1 = [r["u_candidate"][1] - r["u_ref"][1] for r in rows]
    t = [r["t"] for r in rows]

    by_seg = {}
    for r in rows:
        s = segment_name(r["t"])
        by_seg.setdefault(s, []).append(r["u_candidate"][1] - r["u_ref"][1])

    m_u0 = metric_block(du0)
    m_u1 = metric_block(du1)

    lines = [
        "# A/B Step-by-step Report (T2.2)",
        "",
        f"- Dataset: `{DATASET}`",
        f"- Samples: `{len(rows)}`",
        "",
        "## Control deltas (Candidate - Original)",
        "",
        "| Canal | mean|abs| | p95|abs| | max|abs| | RMSE |",
        "|---|---:|---:|---:|---:|",
        f"| u_accel | {m_u0['mean_abs']:.6f} | {m_u0['p95_abs']:.6f} | {m_u0['max_abs']:.6f} | {m_u0['rmse']:.6f} |",
        f"| u_brake | {m_u1['mean_abs']:.6f} | {m_u1['p95_abs']:.6f} | {m_u1['max_abs']:.6f} | {m_u1['rmse']:.6f} |",
        "",
        "## Segmentacion de frenado (u_brake)",
        "",
        "| Segmento | Samples | mean|abs| | p95|abs| | max|abs| | RMSE |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    ordered = ["early_0_2s", "mid_2_5s", "transition_5_6_5s", "late_6_5_8s"]
    for seg in ordered:
        vals = by_seg.get(seg, [])
        if not vals:
            continue
        m = metric_block(vals)
        lines.append(
            f"| {seg} | {len(vals)} | {m['mean_abs']:.6f} | {m['p95_abs']:.6f} | {m['max_abs']:.6f} | {m['rmse']:.6f} |"
        )

    lines += [
        "",
        "## Criterio T2.2",
        "- Requisito: reporte automatico con metricas max/mean/p95 por canal y segmento.",
        "- Resultado: PASS.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"PASS: report generated at {OUT_MD}")


if __name__ == "__main__":
    main()
