#!/bin/bash
# run_frequency_sweep.sh
#
# Sweep GVSoC effective frequency by overriding chip cycle time and running
# the standard SHARC+GVSoC flow for each point.
#
# Usage:
#   source venv/bin/activate
#   bash SHARCBRIDGE/scripts/run_frequency_sweep.sh [config.json]
#
# Env:
#   GVSOC_FREQS_MHZ="400 600 800 1000"   # default
#
# Outputs:
#   /tmp/sharc_freq_sweep/<timestamp>/
#     logs/
#     plots/<freq>MHz.png
#     metrics/<freq>MHz_metrics.json
#     summary.csv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/run_gvsoc_config.sh"

CONFIG_NAME="${1:-gvsoc_figure5.json}"
FREQS_MHZ="${GVSOC_FREQS_MHZ:-400 600 800 1000}"
TIMESTAMP="$(date +%Y-%m-%d--%H-%M-%S)"
OUT_ROOT="/tmp/sharc_freq_sweep/${TIMESTAMP}"

mkdir -p "$OUT_ROOT/logs" "$OUT_ROOT/plots" "$OUT_ROOT/metrics"

CSV="$OUT_ROOT/summary.csv"
echo "freq_mhz,cycle_time_ns,run_dir,avg_delay_s,avg_raw_cycles,avg_scaled_cycles,rmse_u_accel,rmse_u_brake,rmse_x_pos,rmse_x_vel" > "$CSV"

echo "Frequency sweep config: $CONFIG_NAME"
echo "Frequencies (MHz): $FREQS_MHZ"
echo "Output root: $OUT_ROOT"

for freq in $FREQS_MHZ; do
  cycle_ns="$(awk -v f="$freq" 'BEGIN { printf "%.9f", 1000.0 / f }')"
  log="$OUT_ROOT/logs/run_${freq}MHz.log"

  echo
  echo "=== Running ${freq} MHz (cycle_time_ns=${cycle_ns}) ==="

  GVSOC_CHIP_CYCLE_NS="$cycle_ns" bash "$RUNNER" "$CONFIG_NAME" | tee "$log"

  run_dir="$(grep '^Output directory:' "$log" | tail -n 1 | sed 's/^Output directory: //')"
  if [ -z "$run_dir" ] || [ ! -d "$run_dir" ]; then
    echo "ERROR: could not parse run directory from $log"
    exit 1
  fi

  plot_src="$run_dir/latest/plots.png"
  if [ ! -f "$plot_src" ]; then
    echo "ERROR: missing plot for ${freq}MHz: $plot_src"
    exit 1
  fi
  cp "$plot_src" "$OUT_ROOT/plots/${freq}MHz.png"

  python3 - "$run_dir" "$freq" "$cycle_ns" "$OUT_ROOT/metrics/${freq}MHz_metrics.json" "$CSV" <<'PYEOF'
import csv
import glob
import json
import math
import os
import sys

run_dir, freq, cycle_ns, metrics_out, csv_out = sys.argv[1:6]

files = sorted(glob.glob(os.path.join(run_dir, "**", "simulation_data_incremental.json"), recursive=True))
if len(files) < 2:
    raise RuntimeError(f"Expected at least 2 simulation_data_incremental.json files in {run_dir}")

data_by_name = {}
for path in files:
    name = os.path.basename(os.path.dirname(path))
    with open(path, "r", encoding="utf-8") as fh:
        data_by_name[name] = json.load(fh)

baseline_key = "baseline-no-delay-onestep"
gvsoc_key = "gvsoc-real-delays"
if baseline_key not in data_by_name or gvsoc_key not in data_by_name:
    keys = ", ".join(sorted(data_by_name.keys()))
    raise RuntimeError(f"Could not find expected experiments ({baseline_key}, {gvsoc_key}). Got: {keys}")

base = data_by_name[baseline_key]
gvs = data_by_name[gvsoc_key]

def col(arr, j):
    return [row[j] for row in arr]

def rmse(a, b):
    n = min(len(a), len(b))
    if n == 0:
        return float("nan")
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n)) / n)

metrics = {
    "freq_mhz": int(float(freq)),
    "cycle_time_ns": float(cycle_ns),
    "run_dir": run_dir,
    "plot": os.path.join(run_dir, "latest", "plots.png"),
    "rmse_u_accel": rmse(col(gvs["u"], 0), col(base["u"], 0)),
    "rmse_u_brake": rmse(col(gvs["u"], 1), col(base["u"], 1)),
    "rmse_x_pos": rmse(col(gvs["x"], 0), col(base["x"], 0)),
    "rmse_x_vel": rmse(col(gvs["x"], 1), col(base["x"], 1)),
}

pending = gvs.get("pending_computation", []) or gvs.get("pending_computations", [])
if pending:
    delays = [float(pc.get("delay", 0.0)) for pc in pending]
    raw_cycles = [float(pc.get("metadata", {}).get("cycles", 0.0)) for pc in pending]
    scaled_cycles = [float(pc.get("metadata", {}).get("scaled_cycles_for_delay", pc.get("metadata", {}).get("cycles", 0.0))) for pc in pending]
    metrics["avg_delay_s"] = sum(delays) / len(delays)
    metrics["avg_raw_cycles"] = sum(raw_cycles) / len(raw_cycles)
    metrics["avg_scaled_cycles"] = sum(scaled_cycles) / len(scaled_cycles)
else:
    metrics["avg_delay_s"] = float("nan")
    metrics["avg_raw_cycles"] = float("nan")
    metrics["avg_scaled_cycles"] = float("nan")

with open(metrics_out, "w", encoding="utf-8") as fh:
    json.dump(metrics, fh, indent=2)

with open(csv_out, "a", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh)
    writer.writerow([
        metrics["freq_mhz"],
        metrics["cycle_time_ns"],
        metrics["run_dir"],
        metrics["avg_delay_s"],
        metrics["avg_raw_cycles"],
        metrics["avg_scaled_cycles"],
        metrics["rmse_u_accel"],
        metrics["rmse_u_brake"],
        metrics["rmse_x_pos"],
        metrics["rmse_x_vel"],
    ])
PYEOF

  echo "✓ ${freq}MHz complete"
done

echo
echo "Sweep complete."
echo "Summary CSV: $CSV"
echo "Plots dir:   $OUT_ROOT/plots"
echo "Metrics dir: $OUT_ROOT/metrics"
