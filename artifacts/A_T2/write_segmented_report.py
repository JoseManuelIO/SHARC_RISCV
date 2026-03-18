#!/usr/bin/env python3
import json
import math
from pathlib import Path
from statistics import mean


DATASET = Path("artifacts/A_T2/ab_dataset.jsonl")
OUT = Path("artifacts/A_T2/ab_segmented_report.md")


def percentile(values, p):
    arr = sorted(values)
    if not arr:
        return float("nan")
    if len(arr) == 1:
        return arr[0]
    pos = (len(arr) - 1) * (p / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return arr[lo]
    w = pos - lo
    return arr[lo] * (1 - w) + arr[hi] * w


def segment_name(t):
    if t < 2.0:
        return "early_0_2s"
    if t < 5.0:
        return "mid_2_5s"
    if t < 6.5:
        return "transition_5_6_5s"
    return "late_6_5_8s"


def main():
    rows = [json.loads(ln) for ln in DATASET.read_text().splitlines() if ln.strip()]
    by_seg = {}
    for r in rows:
        s = segment_name(r["t"])
        by_seg.setdefault(s, []).append(r["u_candidate"][1] - r["u_ref"][1])

    ordered = ["early_0_2s", "mid_2_5s", "transition_5_6_5s", "late_6_5_8s"]
    lines = [
        "# A/B Segmented Report (T2.3)",
        "",
        f"- Fuente de calculo: `{DATASET}`",
        "- Escenario: A/B onestep (a-original-onestep vs b-gvsoc-onestep)",
        f"- Samples: {len(rows)}",
        "",
        "## Error de frenado por fase",
        "| Segmento | Samples | MAE | p95 abs | Max abs | RMSE | mean signed |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for s in ordered:
        vals = by_seg.get(s, [])
        if not vals:
            continue
        mae = mean([abs(v) for v in vals])
        p95 = percentile([abs(v) for v in vals], 95)
        mmax = max([abs(v) for v in vals])
        rms = math.sqrt(mean([v * v for v in vals]))
        signed = mean(vals)
        lines.append(
            f"| {s} | {len(vals)} | {mae:.6f} | {p95:.6f} | {mmax:.6f} | {rms:.6f} | {signed:.6f} |"
        )

    lines += [
        "",
        "## Criterio T2.3",
        "- Requisito: reporte segmentado por fases de aceleracion/crucero/frenado.",
        "- Resultado: PASS.",
    ]

    OUT.write_text("\n".join(lines) + "\n")
    print(f"PASS: wrote {OUT}")


if __name__ == "__main__":
    main()
