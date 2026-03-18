#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from statistics import mean


ROOT = Path("/tmp/sharc_runs")
OUT_DIR = Path("artifacts/A_T1/sharc_reference")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def collect_original_runs():
    files = sorted(ROOT.glob("**/a-original-onestep/simulation_data_incremental.json"))
    rows = []
    for f in files:
        data = json.loads(f.read_text())
        t = data.get("t", [])
        x = data.get("x", [])
        u = data.get("u", [])

        valid = bool(t) and bool(x) and bool(u) and len(t) == len(x) == len(u)
        row = {
            "file": str(f),
            "valid": int(valid),
            "n_samples": len(t),
            "t_start": t[0] if t else None,
            "t_end": t[-1] if t else None,
            "x0_p": x[0][0] if x else None,
            "x0_h": x[0][1] if x else None,
            "x0_v": x[0][2] if x else None,
            "xN_p": x[-1][0] if x else None,
            "xN_h": x[-1][1] if x else None,
            "xN_v": x[-1][2] if x else None,
            "u_brake_mean": mean([ui[1] for ui in u]) if u else None,
            "u_accel_mean": mean([ui[0] for ui in u]) if u else None,
        }
        rows.append(row)
    return rows


def write_csv(rows, path):
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def write_md(rows, path):
    total = len(rows)
    valid = sum(r["valid"] for r in rows)
    lines = [
        "# SHARC Original Reference Summary (T1.3)",
        "",
        f"- Runs detectadas: {total}",
        f"- Runs validas: {valid}",
        "",
    ]
    if rows:
        best = rows[-1]
        lines += [
            "## Ultima referencia detectada",
            f"- File: `{best['file']}`",
            f"- n_samples: `{best['n_samples']}`",
            f"- t_end: `{best['t_end']}`",
            f"- xN: `[{best['xN_p']}, {best['xN_h']}, {best['xN_v']}]`",
            "",
            "## Criterio T1.3",
            "- Requisito: integridad de resultados por escenario de referencia.",
            f"- Resultado: {'PASS' if valid == total and total > 0 else 'FAIL'}.",
        ]
    else:
        lines += [
            "## Criterio T1.3",
            "- Requisito: integridad de resultados por escenario de referencia.",
            "- Resultado: FAIL (no se detectaron runs).",
        ]

    path.write_text("\n".join(lines) + "\n")


def main():
    rows = collect_original_runs()
    write_csv(rows, OUT_DIR / "sharc_original_reference_runs.csv")
    write_md(rows, OUT_DIR / "summary.md")
    if not rows:
        raise SystemExit(1)
    if any(r["valid"] != 1 for r in rows):
        raise SystemExit(2)
    print(f"PASS: {len(rows)} runs originales validas consolidadas.")


if __name__ == "__main__":
    main()
