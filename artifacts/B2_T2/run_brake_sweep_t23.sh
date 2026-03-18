#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

source venv/bin/activate

STAMP="$(date +%Y-%m-%d--%H-%M-%S)"
OUT_DIR="artifacts/B2_T2/sweep_${STAMP}"
mkdir -p "$OUT_DIR"

BASE_JSON="artifacts/B2_T2/baseline_metrics_2runs.json"
if [ ! -f "$BASE_JSON" ]; then
  echo "ERROR: Missing baseline file: $BASE_JSON"
  exit 1
fi

RESULTS_CSV="$OUT_DIR/results.csv"
RESULTS_JSONL="$OUT_DIR/results.jsonl"
SUMMARY_MD="$OUT_DIR/summary.md"

echo "name,run_dir,rmse_u_accel,rmse_u_brake,mae_u_accel,mae_u_brake,seg_2_5,seg_5_6_5,seg_6_5_8,plot" > "$RESULTS_CSV"
: > "$RESULTS_JSONL"

configs=(
  "baseline|"
  "c1_soft_cap|-DMPC_MARGIN_TRIGGER=-0.8f -DMPC_SAFETY_CLOSE_GAIN=195.0f -DMPC_SAFETY_MARGIN_GAIN=30.0f -DMPC_BRAKE_CAP_MARGIN_POS=4.5f -DMPC_BRAKE_CAP_BASE=980.0f -DMPC_BRAKE_CAP_SPEED_GAIN=235.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=15.0f -DMPC_BRAKE_CAP_MAX=2700.0f"
  "c2_earlier_guard|-DMPC_MARGIN_TRIGGER=-0.6f -DMPC_SAFETY_CLOSE_GAIN=205.0f -DMPC_SAFETY_MARGIN_GAIN=33.0f -DMPC_BRAKE_CAP_MARGIN_POS=5.0f -DMPC_BRAKE_CAP_BASE=1000.0f -DMPC_BRAKE_CAP_SPEED_GAIN=240.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=14.0f -DMPC_BRAKE_CAP_MAX=2800.0f"
  "c3_late_release|-DMPC_MARGIN_TRIGGER=-1.1f -DMPC_SAFETY_CLOSE_GAIN=190.0f -DMPC_SAFETY_MARGIN_GAIN=29.0f -DMPC_BRAKE_CAP_MARGIN_POS=3.2f -DMPC_BRAKE_CAP_BASE=850.0f -DMPC_BRAKE_CAP_SPEED_GAIN=220.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=19.0f -DMPC_BRAKE_CAP_MAX=2200.0f"
)

for cfg in "${configs[@]}"; do
  name="${cfg%%|*}"
  defs="${cfg#*|}"

  echo "[SWEEP] Building $name"
  if [ -n "$defs" ]; then
    make -C SHARCBRIDGE/mpc clean all USER_DEFINES="$defs" > "$OUT_DIR/${name}_build.log" 2>&1
  else
    make -C SHARCBRIDGE/mpc clean all > "$OUT_DIR/${name}_build.log" 2>&1
  fi

  echo "[SWEEP] Running A/B $name"
  run_log="$OUT_DIR/${name}_run.log"
  bash SHARCBRIDGE/scripts/run_gvsoc_config.sh ab_onestep_compare.json > "$run_log" 2>&1

  run_dir="$(grep -m1 '^Out dir:' "$run_log" | awk '{print $3}')"
  if [ -z "$run_dir" ] || [ ! -d "$run_dir" ]; then
    run_dir="$(ls -1td /tmp/sharc_runs/*-ab_onestep_compare 2>/dev/null | head -1)"
  fi
  if [ -z "$run_dir" ] || [ ! -d "$run_dir" ]; then
    echo "ERROR: could not resolve run dir for $name"
    exit 1
  fi

  python3 - "$run_dir" "$name" "$RESULTS_CSV" "$RESULTS_JSONL" <<'PY'
import csv
import json
import math
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
name = sys.argv[2]
csv_path = Path(sys.argv[3])
jsonl_path = Path(sys.argv[4])

a_path = next(run_dir.glob('**/a-original-onestep/simulation_data_incremental.json'))
b_path = next(run_dir.glob('**/b-gvsoc-onestep/simulation_data_incremental.json'))
a = json.load(open(a_path, encoding='utf-8'))
b = json.load(open(b_path, encoding='utf-8'))


def col(arr, i):
    return [x[i] for x in arr]


def rmse(x, y):
    n = min(len(x), len(y))
    return math.sqrt(sum((x[i] - y[i]) ** 2 for i in range(n)) / n)


def mae(x, y):
    n = min(len(x), len(y))
    return sum(abs(x[i] - y[i]) for i in range(n)) / n


def seg_rmse(t, x, y, t0, t1):
    vals = [(x[i] - y[i]) ** 2 for i, tt in enumerate(t[: min(len(t), len(x), len(y))]) if t0 <= tt < t1]
    return math.sqrt(sum(vals) / len(vals)) if vals else float('nan')

u0_ref, u1_ref = col(a['u'], 0), col(a['u'], 1)
u0_can, u1_can = col(b['u'], 0), col(b['u'], 1)
t = a['t']

row = {
    'name': name,
    'run_dir': str(run_dir),
    'rmse_u_accel': rmse(u0_ref, u0_can),
    'rmse_u_brake': rmse(u1_ref, u1_can),
    'mae_u_accel': mae(u0_ref, u0_can),
    'mae_u_brake': mae(u1_ref, u1_can),
    'seg_2_5': seg_rmse(t, u1_ref, u1_can, 2.0, 5.0),
    'seg_5_6_5': seg_rmse(t, u1_ref, u1_can, 5.0, 6.5),
    'seg_6_5_8': seg_rmse(t, u1_ref, u1_can, 6.5, 8.0),
    'plot': str(run_dir / 'latest' / 'plots.png'),
}

with csv_path.open('a', encoding='utf-8', newline='') as fh:
    writer = csv.writer(fh)
    writer.writerow([
        row['name'], row['run_dir'], row['rmse_u_accel'], row['rmse_u_brake'],
        row['mae_u_accel'], row['mae_u_brake'], row['seg_2_5'], row['seg_5_6_5'], row['seg_6_5_8'], row['plot']
    ])

with jsonl_path.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(row) + '\n')

print(json.dumps(row))
PY

done

python3 - "$BASE_JSON" "$RESULTS_JSONL" "$SUMMARY_MD" <<'PY'
import json
import statistics
import sys
from pathlib import Path

base = json.load(open(sys.argv[1], encoding='utf-8'))
rows = [json.loads(line) for line in open(sys.argv[2], encoding='utf-8') if line.strip()]
out = Path(sys.argv[3])

base_rmse_brake = statistics.mean(r['rmse_u_brake'] for r in base)
base_rmse_accel = statistics.mean(r['rmse_u_accel'] for r in base)
base_seg_2_5 = statistics.mean(r['seg_brake_rmse_2_5'] for r in base)
base_seg_6_5_8 = statistics.mean(r['seg_brake_rmse_6_5_8'] for r in base)

for r in rows:
    r['gate_brake'] = r['rmse_u_brake'] < base_rmse_brake
    r['gate_accel'] = r['rmse_u_accel'] <= base_rmse_accel * 1.02
    r['gate_mid'] = r['seg_2_5'] <= base_seg_2_5 * 1.05
    r['gate_late'] = r['seg_6_5_8'] <= base_seg_6_5_8
    r['gate_pass'] = r['gate_brake'] and r['gate_accel'] and r['gate_mid'] and r['gate_late']

passes = [r for r in rows if r['gate_pass']]
best = min(passes, key=lambda r: r['rmse_u_brake']) if passes else min(rows, key=lambda r: r['rmse_u_brake'])

lines = []
lines.append('# T2.3 Brake Sweep Result')
lines.append('')
lines.append('## Baseline thresholds')
lines.append(f'- rmse_u_brake baseline: `{base_rmse_brake:.6f}`')
lines.append(f'- rmse_u_accel baseline: `{base_rmse_accel:.6f}`')
lines.append(f'- seg_2_5 baseline: `{base_seg_2_5:.6f}`')
lines.append(f'- seg_6_5_8 baseline: `{base_seg_6_5_8:.6f}`')
lines.append('')
lines.append('## Candidates')
lines.append('| name | rmse_u_accel | rmse_u_brake | seg_2_5 | seg_5_6_5 | seg_6_5_8 | gate |')
lines.append('|---|---:|---:|---:|---:|---:|---|')
for r in rows:
    lines.append(
        f"| {r['name']} | {r['rmse_u_accel']:.6f} | {r['rmse_u_brake']:.6f} | "
        f"{r['seg_2_5']:.6f} | {r['seg_5_6_5']:.6f} | {r['seg_6_5_8']:.6f} | {'PASS' if r['gate_pass'] else 'FAIL'} |"
    )
lines.append('')
lines.append('## Selection')
lines.append(f"- Best candidate by rmse_u_brake: `{best['name']}`")
lines.append(f"- Selected run: `{best['run_dir']}`")
lines.append(f"- Plot: `{best['plot']}`")
lines.append(f"- Gate status: `{'PASS' if best['gate_pass'] else 'FAIL'}`")

out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(out)
PY

# Restore default build state after sweep.
make -C SHARCBRIDGE/mpc clean all > "$OUT_DIR/restore_default_build.log" 2>&1

echo "Sweep complete: $OUT_DIR"
echo "Summary: $SUMMARY_MD"
