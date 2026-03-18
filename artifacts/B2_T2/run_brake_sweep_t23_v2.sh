#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"
source venv/bin/activate

STAMP="$(date +%Y-%m-%d--%H-%M-%S)"
OUT_DIR="artifacts/B2_T2/sweep_v2_${STAMP}"
mkdir -p "$OUT_DIR"

BASE_JSON="artifacts/B2_T2/baseline_metrics_2runs.json"
RESULTS_CSV="$OUT_DIR/results.csv"
RESULTS_JSONL="$OUT_DIR/results.jsonl"
SUMMARY_MD="$OUT_DIR/summary.md"

echo "name,run_dir,rmse_u_accel,rmse_u_brake,mae_u_accel,mae_u_brake,seg_2_5,seg_5_6_5,seg_6_5_8,plot" > "$RESULTS_CSV"
: > "$RESULTS_JSONL"

configs=(
  "baseline|"
  "d1_aggr|-DMPC_W_DU_BRAKE=0.15f -DMPC_W_HEADWAY=90.0f -DMPC_MARGIN_TRIGGER=-0.8f -DMPC_SAFETY_CLOSE_GAIN=210.0f -DMPC_SAFETY_MARGIN_GAIN=34.0f -DMPC_BRAKE_CAP_MARGIN_POS=4.5f -DMPC_BRAKE_CAP_BASE=1050.0f -DMPC_BRAKE_CAP_SPEED_GAIN=260.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=14.0f -DMPC_BRAKE_CAP_MAX=3200.0f"
  "d2_no_release|-DMPC_W_DU_BRAKE=0.20f -DMPC_W_HEADWAY=85.0f -DMPC_MARGIN_TRIGGER=-0.7f -DMPC_SAFETY_CLOSE_GAIN=205.0f -DMPC_SAFETY_MARGIN_GAIN=33.0f -DMPC_BRAKE_CAP_MARGIN_POS=8.0f -DMPC_BRAKE_CAP_BASE=2200.0f -DMPC_BRAKE_CAP_SPEED_GAIN=120.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=8.0f -DMPC_BRAKE_CAP_MAX=4200.0f"
  "d3_transition|-DMPC_W_DU_BRAKE=0.18f -DMPC_W_HEADWAY=105.0f -DMPC_MARGIN_TRIGGER=-0.5f -DMPC_SAFETY_CLOSE_GAIN=220.0f -DMPC_SAFETY_MARGIN_GAIN=38.0f -DMPC_BRAKE_CAP_MARGIN_POS=5.5f -DMPC_BRAKE_CAP_BASE=1200.0f -DMPC_BRAKE_CAP_SPEED_GAIN=250.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=12.0f -DMPC_BRAKE_CAP_MAX=3400.0f"
  "d4_hard_safety|-DMPC_W_DU_BRAKE=0.10f -DMPC_W_HEADWAY=120.0f -DMPC_MARGIN_TRIGGER=-0.3f -DMPC_SAFETY_CLOSE_GAIN=240.0f -DMPC_SAFETY_MARGIN_GAIN=45.0f -DMPC_BRAKE_CAP_MARGIN_POS=6.0f -DMPC_BRAKE_CAP_BASE=1500.0f -DMPC_BRAKE_CAP_SPEED_GAIN=210.0f -DMPC_BRAKE_CAP_MARGIN_SLOPE=10.0f -DMPC_BRAKE_CAP_MAX=3600.0f"
)

for cfg in "${configs[@]}"; do
  name="${cfg%%|*}"
  defs="${cfg#*|}"
  echo "[SWEEP_V2] Building $name"
  if [ -n "$defs" ]; then
    make -C SHARCBRIDGE/mpc clean all USER_DEFINES="$defs" > "$OUT_DIR/${name}_build.log" 2>&1
  else
    make -C SHARCBRIDGE/mpc clean all > "$OUT_DIR/${name}_build.log" 2>&1
  fi

  echo "[SWEEP_V2] Running A/B $name"
  run_log="$OUT_DIR/${name}_run.log"
  bash SHARCBRIDGE/scripts/run_gvsoc_config.sh ab_onestep_compare.json > "$run_log" 2>&1
  run_dir="$(grep -m1 '^Out dir:' "$run_log" | awk '{print $3}')"
  if [ -z "$run_dir" ] || [ ! -d "$run_dir" ]; then
    run_dir="$(ls -1td /tmp/sharc_runs/*-ab_onestep_compare 2>/dev/null | head -1)"
  fi

  python3 - "$run_dir" "$name" "$RESULTS_CSV" "$RESULTS_JSONL" <<'PY'
import csv, json, math, sys
from pathlib import Path
run_dir = Path(sys.argv[1]); name = sys.argv[2]; csv_path = Path(sys.argv[3]); jsonl_path = Path(sys.argv[4])
a = json.load(open(next(run_dir.glob('**/a-original-onestep/simulation_data_incremental.json')), encoding='utf-8'))
b = json.load(open(next(run_dir.glob('**/b-gvsoc-onestep/simulation_data_incremental.json')), encoding='utf-8'))

def col(arr,i): return [x[i] for x in arr]
def rmse(x,y):
    n=min(len(x),len(y)); return math.sqrt(sum((x[i]-y[i])**2 for i in range(n))/n)
def mae(x,y):
    n=min(len(x),len(y)); return sum(abs(x[i]-y[i]) for i in range(n))/n
def seg_rmse(t,x,y,t0,t1):
    vals=[(x[i]-y[i])**2 for i,tt in enumerate(t[:min(len(t),len(x),len(y))]) if t0<=tt<t1]
    return math.sqrt(sum(vals)/len(vals)) if vals else float('nan')

u0_ref,u1_ref = col(a['u'],0),col(a['u'],1)
u0_can,u1_can = col(b['u'],0),col(b['u'],1)
t=a['t']
row={
 'name':name,'run_dir':str(run_dir),
 'rmse_u_accel':rmse(u0_ref,u0_can),'rmse_u_brake':rmse(u1_ref,u1_can),
 'mae_u_accel':mae(u0_ref,u0_can),'mae_u_brake':mae(u1_ref,u1_can),
 'seg_2_5':seg_rmse(t,u1_ref,u1_can,2.0,5.0),
 'seg_5_6_5':seg_rmse(t,u1_ref,u1_can,5.0,6.5),
 'seg_6_5_8':seg_rmse(t,u1_ref,u1_can,6.5,8.0),
 'plot':str(run_dir/'latest'/'plots.png')
}
with csv_path.open('a',encoding='utf-8',newline='') as fh:
    csv.writer(fh).writerow([row[k] for k in ['name','run_dir','rmse_u_accel','rmse_u_brake','mae_u_accel','mae_u_brake','seg_2_5','seg_5_6_5','seg_6_5_8','plot']])
with jsonl_path.open('a',encoding='utf-8') as fh:
    fh.write(json.dumps(row)+'\n')
print(json.dumps(row))
PY
done

python3 - "$BASE_JSON" "$RESULTS_JSONL" "$SUMMARY_MD" <<'PY'
import json, statistics, sys
base = json.load(open(sys.argv[1], encoding='utf-8'))
rows = [json.loads(line) for line in open(sys.argv[2], encoding='utf-8') if line.strip()]
base_rmse_brake = statistics.mean(r['rmse_u_brake'] for r in base)
base_rmse_accel = statistics.mean(r['rmse_u_accel'] for r in base)
base_seg_2_5 = statistics.mean(r['seg_brake_rmse_2_5'] for r in base)
base_seg_6_5_8 = statistics.mean(r['seg_brake_rmse_6_5_8'] for r in base)
for r in rows:
    r['gate_pass'] = (
        r['rmse_u_brake'] < base_rmse_brake and
        r['rmse_u_accel'] <= base_rmse_accel * 1.02 and
        r['seg_2_5'] <= base_seg_2_5 * 1.05 and
        r['seg_6_5_8'] <= base_seg_6_5_8
    )
best = min(rows, key=lambda r: r['rmse_u_brake'])
with open(sys.argv[3], 'w', encoding='utf-8') as fh:
    fh.write('# T2.3 Brake Sweep V2 Result\n\n')
    fh.write(f"- baseline rmse_u_brake: `{base_rmse_brake:.6f}`\n")
    fh.write(f"- baseline rmse_u_accel: `{base_rmse_accel:.6f}`\n\n")
    fh.write('| name | rmse_u_accel | rmse_u_brake | seg_2_5 | seg_5_6_5 | seg_6_5_8 | gate |\n')
    fh.write('|---|---:|---:|---:|---:|---:|---|\n')
    for r in rows:
        fh.write(f"| {r['name']} | {r['rmse_u_accel']:.6f} | {r['rmse_u_brake']:.6f} | {r['seg_2_5']:.6f} | {r['seg_5_6_5']:.6f} | {r['seg_6_5_8']:.6f} | {'PASS' if r['gate_pass'] else 'FAIL'} |\n")
    fh.write('\n')
    fh.write(f"- best by rmse_u_brake: `{best['name']}`\n")
    fh.write(f"- selected run: `{best['run_dir']}`\n")
print(sys.argv[3])
PY

make -C SHARCBRIDGE/mpc clean all > "$OUT_DIR/restore_default_build.log" 2>&1

echo "Sweep v2 complete: $OUT_DIR"
echo "Summary: $SUMMARY_MD"
