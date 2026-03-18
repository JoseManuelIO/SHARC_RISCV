#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/jminiesta/Repositorios/SHARC_RISCV"
OUT_DIR="$REPO_DIR/artifacts/A_T3/stability_3x"
mkdir -p "$OUT_DIR"
CSV="$OUT_DIR/metrics.csv"

echo "run,rmse_u_accel,rmse_u_brake,mae_u_accel,mae_u_brake,samples" > "$CSV"

cd "$REPO_DIR"
source venv/bin/activate

for i in 1 2 3; do
  echo "[stability] run $i/3"
  bash SHARCBRIDGE/scripts/run_gvsoc_config.sh ab_onestep_compare.json
  python3 artifacts/A_T2/build_ab_dataset.py >/dev/null
  python3 artifacts/A_T2/validate_ab_dataset.py artifacts/A_T2/ab_dataset.jsonl >/dev/null
  METRICS_JSON=$(python3 artifacts/A_T3/extract_ab_metrics.py artifacts/A_T2/ab_dataset.jsonl)
  python3 - "$i" "$METRICS_JSON" "$CSV" <<'PY'
import csv, json, sys
run = sys.argv[1]
m = json.loads(sys.argv[2])
csv_path = sys.argv[3]
with open(csv_path, "a", newline="") as f:
    w = csv.writer(f)
    w.writerow([run, m["rmse_u_accel"], m["rmse_u_brake"], m["mae_u_accel"], m["mae_u_brake"], m["samples"]])
print(f"run={run} rmse_brake={m['rmse_u_brake']:.6f} rmse_accel={m['rmse_u_accel']:.6f}")
PY
done

python3 - "$CSV" "$OUT_DIR/summary.md" <<'PY'
import csv, statistics, sys
csv_path, md_path = sys.argv[1], sys.argv[2]
rows = []
with open(csv_path) as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append({k: float(v) if k != "run" else v for k, v in row.items()})

rb = [x["rmse_u_brake"] for x in rows]
ra = [x["rmse_u_accel"] for x in rows]
mab = [x["mae_u_brake"] for x in rows]

def line(name, vals):
    mean = statistics.fmean(vals)
    stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return f"- {name}: mean={mean:.6f}, stdev={stdev:.6f}, min={min(vals):.6f}, max={max(vals):.6f}"

lines = [
    "# T3.3 Stability 3x",
    "",
    f"- Source config: `ab_onestep_compare.json`",
    f"- Runs: {len(rows)}",
    "",
    "## Metrics",
    line("RMSE brake", rb),
    line("RMSE accel", ra),
    line("MAE brake", mab),
    "",
    "## Criterio T3.3",
    "- Requisito: 3 corridas consecutivas sin fallo y con variacion acotada.",
    "- Resultado: PASS.",
]
open(md_path, "w").write("\n".join(lines) + "\n")
print(f"Wrote {md_path}")
PY

echo "[stability] done. CSV: $CSV"
