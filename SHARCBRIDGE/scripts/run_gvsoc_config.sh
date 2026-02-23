#!/bin/bash
# run_gvsoc_config.sh
#
# Generic SHARC + GVSoC runner for a single simulation config file.
#
# Usage:
#   source venv/bin/activate
#   bash SHARCBRIDGE/scripts/run_gvsoc_config.sh gvsoc_test.json
#
# Output:
#   /tmp/sharc_runs/<timestamp>-<config_name>/

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <config_filename.json>"
  exit 1
fi

CONFIG_NAME="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARCBRIDGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$SHARCBRIDGE_DIR/.." && pwd)"

FLASK_SERVER="$SCRIPT_DIR/gvsoc_flask_server.py"
WRAPPER_HOST="$SHARCBRIDGE_DIR/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py"

CONFIG_HOST="$REPO_DIR/sharc_original/examples/acc_example/simulation_configs/$CONFIG_NAME"
CONFIG_DOCKER="/home/dcuser/examples/acc_example/simulation_configs/$CONFIG_NAME"

FLASK_PORT="${FLASK_PORT:-5000}"
TIMESTAMP="$(date +%Y-%m-%d--%H-%M-%S)"
RUN_NAME="${CONFIG_NAME%.json}"
OUT_DIR="/tmp/sharc_runs/${TIMESTAMP}-${RUN_NAME}"

SHARC_CONTAINER="sharc_run_${RUN_NAME}"
SHARC_CONTAINER="${SHARC_CONTAINER//[^a-zA-Z0-9_.-]/_}"
DOCKER_ENV_ARGS=()
if [ -n "${GVSOC_CHIP_CYCLE_NS:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_CHIP_CYCLE_NS=${GVSOC_CHIP_CYCLE_NS}")
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

FLASK_PID=""
FLASK_OURS=0

cleanup() {
  local exit_code=$?
  echo -e "\n${YELLOW}[Cleanup] Stopping resources...${NC}"
  docker stop "$SHARC_CONTAINER" 2>/dev/null || true
  if [ "$FLASK_OURS" -eq 1 ] && [ -n "$FLASK_PID" ] && kill -0 "$FLASK_PID" 2>/dev/null; then
    curl -sf -X POST "http://localhost:${FLASK_PORT}/shutdown" -o /dev/null 2>/dev/null || true
    sleep 0.5
    kill "$FLASK_PID" 2>/dev/null || true
  fi
  if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}[Cleanup] Done${NC}"
  else
    echo -e "${RED}[Cleanup] Exited with code $exit_code${NC}"
  fi
  exit $exit_code
}
trap cleanup EXIT INT TERM

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SHARC + GVSoC: Generic Config Runner                      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo "Config:    $CONFIG_HOST"
echo "Out dir:   $OUT_DIR"
echo "Container: $SHARC_CONTAINER"
if [ -n "${GVSOC_CHIP_CYCLE_NS:-}" ]; then
  echo "Cycle ns:  ${GVSOC_CHIP_CYCLE_NS} (from env)"
fi

if [ ! -f "$CONFIG_HOST" ]; then
  echo -e "${RED}ERROR: Config not found: $CONFIG_HOST${NC}"
  exit 1
fi

if [ ! -f "$WRAPPER_HOST" ]; then
  echo -e "${RED}ERROR: Wrapper not found: $WRAPPER_HOST${NC}"
  exit 1
fi

mkdir -p "$OUT_DIR"

echo -e "\n${YELLOW}[1/7] Ensuring Flask server...${NC}"
if curl -sf "http://localhost:${FLASK_PORT}/health" -o /dev/null 2>/dev/null; then
  echo -e "${GREEN}✓ Reusing Flask on port ${FLASK_PORT}${NC}"
else
  python3 "$FLASK_SERVER" --host 0.0.0.0 --port "$FLASK_PORT" --skip-validation > /tmp/flask_generic.log 2>&1 &
  FLASK_PID=$!
  FLASK_OURS=1
  echo "Flask PID: $FLASK_PID (log: /tmp/flask_generic.log)"
  WAITED=0
  until curl -sf "http://localhost:${FLASK_PORT}/health" -o /dev/null 2>/dev/null; do
    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
    if [ $WAITED -ge 20 ]; then
      echo -e "\n${RED}ERROR: Flask did not start within 20s${NC}"
      cat /tmp/flask_generic.log || true
      exit 1
    fi
  done
  echo
  echo -e "${GREEN}✓ Flask is ready${NC}"
fi

echo -e "\n${YELLOW}[2/7] Cleaning previous container with same name...${NC}"
docker rm -f "$SHARC_CONTAINER" 2>/dev/null || true
echo -e "${GREEN}✓ Clean${NC}"

echo -e "\n${YELLOW}[3/7] Running SHARC with ${CONFIG_NAME}...${NC}"
docker run \
  --name "$SHARC_CONTAINER" \
  --network=host \
  "${DOCKER_ENV_ARGS[@]}" \
  -v "$OUT_DIR:/home/dcuser/examples/acc_example/experiments" \
  -v "$WRAPPER_HOST:/home/dcuser/examples/acc_example/gvsoc_controller_wrapper_v2.py" \
  -v "$CONFIG_HOST:$CONFIG_DOCKER:ro" \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  sharc --config_filename "$CONFIG_NAME"

echo -e "${GREEN}✓ SHARC finished${NC}"

echo -e "\n${YELLOW}[4/7] Verifying generated data...${NC}"
DATA_COUNT=$(find "$OUT_DIR" -name "simulation_data_incremental.json" | wc -l | tr -d ' ')
echo "simulation_data_incremental.json files: $DATA_COUNT"
if [ "$DATA_COUNT" -lt 1 ]; then
  echo -e "${RED}ERROR: No simulation_data_incremental.json generated${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Output data present${NC}"

echo -e "\n${YELLOW}[5/7] Validating dynamics trace per iteration (k,t,x,w)...${NC}"
python3 - "$OUT_DIR" <<'PYEOF'
import json
import os
import sys

out_dir = sys.argv[1]
trace_files = []
for root, _, files in os.walk(out_dir):
    if "wrapper_dynamics_trace.ndjson" in files:
        trace_files.append(os.path.join(root, "wrapper_dynamics_trace.ndjson"))

if not trace_files:
    print("ERROR: No wrapper_dynamics_trace.ndjson found")
    sys.exit(1)

trace_files.sort()
for path in trace_files:
    rel = os.path.relpath(path, out_dir)
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if not records:
        print(f"ERROR: Empty trace file: {rel}")
        sys.exit(1)
    for idx, rec in enumerate(records):
        for key in ("k", "t", "x", "w"):
            if key not in rec:
                print(f"ERROR: Missing key '{key}' in {rel} line {idx + 1}")
                sys.exit(1)
    print(f"  ✓ {rel}: {len(records)} iterations with k,t,x,w")

print("✓ Dynamics trace validated")
PYEOF

echo -e "\n${YELLOW}[6/7] Generating comparative plot(s)...${NC}"
mkdir -p "$OUT_DIR/latest"
OUT_DIR="$OUT_DIR" python3 - <<'PYEOF'
import glob
import json
import os

out_dir = os.path.abspath(os.environ["OUT_DIR"])
latest_dir = os.path.join(out_dir, "latest")
os.makedirs(latest_dir, exist_ok=True)

data = {}
for sim_path in sorted(glob.glob(os.path.join(out_dir, "**", "simulation_data_incremental.json"), recursive=True)):
    sim = json.load(open(sim_path, "r", encoding="utf-8"))
    cfg_path = os.path.join(os.path.dirname(sim_path), "config.json")
    cfg = json.load(open(cfg_path, "r", encoding="utf-8")) if os.path.exists(cfg_path) else {}

    exp_data = {k: sim.get(k, []) for k in ("k", "t", "x", "u", "w")}
    exp_data["pending_computations"] = sim.get("pending_computation", sim.get("pending_computations", []))
    exp_data["batches"] = sim.get("batches", None)

    label = os.path.basename(os.path.dirname(sim_path)) or os.path.basename(sim_path)
    key = label
    suffix = 1
    while key in data:
        key = f"{label}_{suffix}"
        suffix += 1

    data[key] = {
        "label": label,
        "experiment directory": "/home/dcuser/examples/acc_example/latest",
        "experiment data": exp_data,
        "experiment config": cfg
    }

output_json = os.path.join(latest_dir, "experiment_list_data_incremental.json")
with open(output_json, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
print(f"Wrote {output_json} with {len(data)} experiment(s)")
PYEOF

docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$OUT_DIR:/home/dcuser/examples/acc_example/experiments" \
  -v "$OUT_DIR/latest:/home/dcuser/examples/acc_example/latest" \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  python3 generate_example_figures.py

if [ -f "$OUT_DIR/latest/plots.png" ]; then
  echo -e "${GREEN}✓ Plot generated: $OUT_DIR/latest/plots.png${NC}"
else
  echo -e "${RED}ERROR: Plot was not generated: $OUT_DIR/latest/plots.png${NC}"
  exit 1
fi

echo -e "\n${YELLOW}[7/7] Summary${NC}"
echo "Output directory: $OUT_DIR"
find "$OUT_DIR" -name "simulation_data_incremental.json" | sort
echo "Plot: $OUT_DIR/latest/plots.png"
echo -e "${GREEN}✓ Run complete${NC}"
