#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/jminiesta/Repositorios/SHARC_RISCV"
STAMP="$(date +%Y-%m-%d--%H-%M-%S)"
OUT_DIR="$REPO_DIR/artifacts/B2_T2/stability_10x_${STAMP}"
mkdir -p "$OUT_DIR"
CSV="$OUT_DIR/metrics.csv"

echo "run,rmse_u_accel,rmse_u_brake,mae_u_accel,mae_u_brake,samples,run_dir,plot" > "$CSV"

cd "$REPO_DIR"
source venv/bin/activate

for i in $(seq 1 10); do
  echo "[stability_10x] run $i/10"
  RUN_LOG="$OUT_DIR/run_${i}.log"
  bash SHARCBRIDGE/scripts/run_gvsoc_config.sh ab_onestep_compare.json > "$RUN_LOG" 2>&1
  RUN_DIR=$(grep -m1 '^Out dir:' "$RUN_LOG" | awk '{print $3}')
  if [ -z "$RUN_DIR" ]; then
    RUN_DIR=$(ls -1td /tmp/sharc_runs/*-ab_onestep_compare 2>/dev/null | head -1)
  fi

  python3 artifacts/A_T2/build_ab_dataset.py >/dev/null
  python3 artifacts/A_T2/validate_ab_dataset.py artifacts/A_T2/ab_dataset.jsonl >/dev/null
  METRICS_JSON=$(python3 artifacts/A_T3/extract_ab_metrics.py artifacts/A_T2/ab_dataset.jsonl)
  python3 - "$i" "$METRICS_JSON" "$CSV" "$RUN_DIR" <<'PY'
import csv, json, sys
run = sys.argv[1]
m = json.loads(sys.argv[2])
csv_path = sys.argv[3]
run_dir = sys.argv[4]
plot = run_dir + '/latest/plots.png'
with open(csv_path, 'a', newline='') as f:
    w = csv.writer(f)
    w.writerow([run, m['rmse_u_accel'], m['rmse_u_brake'], m['mae_u_accel'], m['mae_u_brake'], m['samples'], run_dir, plot])
print(f"run={run} rmse_brake={m['rmse_u_brake']:.6f} rmse_accel={m['rmse_u_accel']:.6f}")
PY
done

python3 - "$CSV" "$OUT_DIR/summary.md" <<'PY'
import csv
import statistics
import sys

csv_path, md_path = sys.argv[1], sys.argv[2]
rows = []
with open(csv_path) as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append({
            'run': row['run'],
            'rmse_u_accel': float(row['rmse_u_accel']),
            'rmse_u_brake': float(row['rmse_u_brake']),
            'mae_u_accel': float(row['mae_u_accel']),
            'mae_u_brake': float(row['mae_u_brake']),
            'samples': float(row['samples']),
            'run_dir': row['run_dir'],
            'plot': row['plot'],
        })

rb = [x['rmse_u_brake'] for x in rows]
ra = [x['rmse_u_accel'] for x in rows]
mb = [x['mae_u_brake'] for x in rows]

mean_rb = statistics.fmean(rb)
std_rb = statistics.pstdev(rb)
mean_ra = statistics.fmean(ra)
std_ra = statistics.pstdev(ra)

# Stability gate thresholds for this task.
pass_runs = len(rows) == 10
pass_std = std_rb <= 1.0 and std_ra <= 1.0
status = 'PASS' if pass_runs and pass_std else 'FAIL'

lines = [
    '# B2-T2.5 Stability 10x',
    '',
    '- Source config: `ab_onestep_compare.json`',
    f'- Runs: {len(rows)}',
    '',
    '## Metrics',
    f'- RMSE brake: mean={mean_rb:.6f}, stdev={std_rb:.6f}, min={min(rb):.6f}, max={max(rb):.6f}',
    f'- RMSE accel: mean={mean_ra:.6f}, stdev={std_ra:.6f}, min={min(ra):.6f}, max={max(ra):.6f}',
    f'- MAE brake: mean={statistics.fmean(mb):.6f}, stdev={statistics.pstdev(mb):.6f}',
    '',
    '## Gate',
    '- Requisito: 10/10 corridas sin fallo y variación acotada.',
    '- Umbral aplicado: stdev RMSE brake <= 1.0 y stdev RMSE accel <= 1.0.',
    f'- Resultado: {status}.',
]

with open(md_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print(md_path)
PY

echo "[stability_10x] done: $OUT_DIR"
