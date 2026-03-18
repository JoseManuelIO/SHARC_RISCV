#!/bin/bash
# run_gvsoc_config.sh
#
# Generic SHARC + GVSoC runner for a single simulation config file.
# Official transport path: TCP server.
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
VENV_PY="$REPO_DIR/venv/bin/python3"
if [ -x "$VENV_PY" ]; then
  PYTHON_BIN="$VENV_PY"
else
  PYTHON_BIN="python3"
fi

TCP_SERVER="$SCRIPT_DIR/gvsoc_tcp_server.py"
WRAPPER_HOST="$SHARCBRIDGE_DIR/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py"
BUILD_QP_SCRIPT="$SCRIPT_DIR/build_qp_runtime_profile.sh"
QP_RUNTIME_ELF="$SHARCBRIDGE_DIR/mpc/build/qp_riscv_runtime.elf"

CONFIG_HOST="$REPO_DIR/sharc_original/examples/acc_example/simulation_configs/$CONFIG_NAME"
CONFIG_DOCKER="/home/dcuser/examples/acc_example/simulation_configs/$CONFIG_NAME"

GVSOC_HOST="${GVSOC_HOST:-127.0.0.1}"
GVSOC_PORT="${GVSOC_PORT:-5000}"
GVSOC_BIND_HOST="${GVSOC_BIND_HOST:-0.0.0.0}"
GVSOC_EXEC_MODE="${GVSOC_EXEC_MODE:-persistent}"
GVSOC_PERSISTENT_PATH="${GVSOC_PERSISTENT_PATH:-gvsoc_legacy}"
SHARC_OFFICIAL_RISCV_MODE="${SHARC_OFFICIAL_RISCV_MODE:-1}"
SHARC_DOUBLE_NATIVE="${SHARC_DOUBLE_NATIVE:-1}"
GVSOC_QP_SOLVE="${GVSOC_QP_SOLVE:-}"
GVSOC_QP_PERSISTENT_BACKEND="${GVSOC_QP_PERSISTENT_BACKEND:-}"
GVSOC_QP_PERSISTENT_EXPERIMENTAL="${GVSOC_QP_PERSISTENT_EXPERIMENTAL:-}"
GVSOC_QP_PERSISTENT_ALLOW_FALLBACK="${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK:-}"

if [ "$SHARC_OFFICIAL_RISCV_MODE" = "1" ]; then
  if [ -z "$GVSOC_QP_SOLVE" ]; then
    GVSOC_QP_SOLVE="1"
  fi
  if [ "$GVSOC_QP_SOLVE" != "1" ]; then
    echo "ERROR: SHARC_OFFICIAL_RISCV_MODE=1 requires GVSOC_QP_SOLVE=1"
    exit 1
  fi
  if [ -z "$GVSOC_QP_PERSISTENT_BACKEND" ]; then
    GVSOC_QP_PERSISTENT_BACKEND="proxy"
  fi
  if [ -z "$GVSOC_QP_PERSISTENT_EXPERIMENTAL" ]; then
    GVSOC_QP_PERSISTENT_EXPERIMENTAL="1"
  fi
  if [ -z "$GVSOC_QP_PERSISTENT_ALLOW_FALLBACK" ]; then
    GVSOC_QP_PERSISTENT_ALLOW_FALLBACK="0"
  fi
fi
if [ "$SHARC_DOUBLE_NATIVE" = "1" ]; then
  PULP_SDK_CONFIG="${PULP_SDK_CONFIG:-pulp-open-double.sh}"
  GVSOC_TARGET="${GVSOC_TARGET:-pulp-open}"
else
  PULP_SDK_CONFIG="${PULP_SDK_CONFIG:-pulp-open.sh}"
  GVSOC_TARGET="${GVSOC_TARGET:-pulp-open}"
fi
TIMESTAMP="$(date +%Y-%m-%d--%H-%M-%S)"
RUN_NAME="${CONFIG_NAME%.json}"
OUT_DIR="/tmp/sharc_runs/${TIMESTAMP}-${RUN_NAME}"

SHARC_CONTAINER="sharc_run_${RUN_NAME}"
SHARC_CONTAINER="${SHARC_CONTAINER//[^a-zA-Z0-9_.-]/_}"
DOCKER_ENV_ARGS=(
  -e "GVSOC_TRANSPORT=tcp"
  -e "GVSOC_HOST=${GVSOC_HOST}"
  -e "GVSOC_PORT=${GVSOC_PORT}"
  -e "GVSOC_EXEC_MODE=${GVSOC_EXEC_MODE}"
  -e "GVSOC_PERSISTENT_PATH=${GVSOC_PERSISTENT_PATH}"
  -e "SHARC_OFFICIAL_RISCV_MODE=${SHARC_OFFICIAL_RISCV_MODE}"
)
if [ -n "${GVSOC_CHIP_CYCLE_NS:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_CHIP_CYCLE_NS=${GVSOC_CHIP_CYCLE_NS}")
fi
if [ -n "${GVSOC_QP_SOLVE:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_QP_SOLVE=${GVSOC_QP_SOLVE}")
fi
if [ -n "${GVSOC_QP_PERSISTENT_BACKEND:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_QP_PERSISTENT_BACKEND=${GVSOC_QP_PERSISTENT_BACKEND}")
fi
if [ -n "${GVSOC_QP_PERSISTENT_EXPERIMENTAL:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_QP_PERSISTENT_EXPERIMENTAL=${GVSOC_QP_PERSISTENT_EXPERIMENTAL}")
fi
if [ -n "${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_QP_PERSISTENT_ALLOW_FALLBACK=${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK}")
fi
for v in OMP_NUM_THREADS OPENBLAS_NUM_THREADS MKL_NUM_THREADS; do
  if [ -n "${!v:-}" ]; then
    DOCKER_ENV_ARGS+=(-e "${v}=${!v}")
  fi
done
DOCKER_RUN_ARGS=()
if [ -n "${SHARC_DOCKER_PRIVILEGED:-}" ]; then
  DOCKER_RUN_ARGS+=(--privileged)
fi
if [ -n "${SHARC_DOCKER_CAP_SYS_ADMIN:-}" ]; then
  DOCKER_RUN_ARGS+=(--cap-add=SYS_ADMIN)
fi
if [ -n "${SHARC_DOCKER_SECCOMP_UNCONFINED:-}" ]; then
  DOCKER_RUN_ARGS+=(--security-opt seccomp=unconfined)
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TCP_PID=""

probe_tcp_server() {
  "$PYTHON_BIN" - "$GVSOC_HOST" "$GVSOC_PORT" <<'PYEOF'
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

try:
    with socket.create_connection((host, port), timeout=1.0) as sock:
        sock.settimeout(1.0)
        sock.sendall(b"{}\n")
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk

    if not data:
        raise RuntimeError("no response from server")

    msg = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
    if msg.get("status") == "ERROR" and msg.get("error_code") == "BAD_REQUEST":
        sys.exit(0)
    raise RuntimeError(f"unexpected response: {msg}")
except Exception:
    sys.exit(1)
PYEOF
}

shutdown_tcp_server() {
  "$PYTHON_BIN" - "$GVSOC_HOST" "$GVSOC_PORT" <<'PYEOF'
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

try:
    with socket.create_connection((host, port), timeout=1.0) as sock:
        sock.settimeout(1.0)
        sock.sendall((json.dumps({"type": "shutdown"}) + "\n").encode("utf-8"))
except Exception:
    pass
PYEOF
}

cleanup() {
  local exit_code=$?
  echo -e "\n${YELLOW}[Cleanup] Stopping resources...${NC}"
  docker stop "$SHARC_CONTAINER" 2>/dev/null || true
  if [ -n "$TCP_PID" ] && kill -0 "$TCP_PID" 2>/dev/null; then
    shutdown_tcp_server || true
    sleep 0.3
    kill "$TCP_PID" 2>/dev/null || true
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
echo "Transport: tcp (${GVSOC_HOST}:${GVSOC_PORT})"
echo "TCP bind:  ${GVSOC_BIND_HOST}:${GVSOC_PORT}"
echo "Exec mode: ${GVSOC_EXEC_MODE}"
echo "Path:      ${GVSOC_PERSISTENT_PATH}"
echo "Official:  ${SHARC_OFFICIAL_RISCV_MODE}"
echo "Double:    $SHARC_DOUBLE_NATIVE"
echo "SDK cfg:   $PULP_SDK_CONFIG"
echo "Target:    $GVSOC_TARGET"
if [ -n "${GVSOC_CHIP_CYCLE_NS:-}" ]; then
  echo "Cycle ns:  ${GVSOC_CHIP_CYCLE_NS} (from env)"
fi
if [ -n "${GVSOC_QP_SOLVE:-}" ]; then
  echo "QP solve:  ${GVSOC_QP_SOLVE}"
fi
if [ -n "${GVSOC_QP_PERSISTENT_BACKEND:-}" ]; then
  echo "QP back:   ${GVSOC_QP_PERSISTENT_BACKEND}"
fi
if [ -n "${GVSOC_QP_PERSISTENT_EXPERIMENTAL:-}" ]; then
  echo "QP exper:  ${GVSOC_QP_PERSISTENT_EXPERIMENTAL}"
fi
if [ -n "${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK:-}" ]; then
  echo "QP fb:     ${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK}"
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

if [ "${GVSOC_QP_SOLVE:-0}" = "1" ]; then
  echo -e "\n${YELLOW}[0/7] Preparing QP runtime ELF...${NC}"
  PROFILE="single"
  if [ "$SHARC_DOUBLE_NATIVE" = "1" ]; then
    PROFILE="double"
  fi
  if [ "${SHARC_SKIP_BUILD:-0}" != "1" ]; then
    bash "$BUILD_QP_SCRIPT" "$PROFILE"
  elif [ ! -f "$QP_RUNTIME_ELF" ]; then
    echo -e "${RED}ERROR: Missing $QP_RUNTIME_ELF and SHARC_SKIP_BUILD=1${NC}"
    echo -e "${RED}Build it with: bash SHARCBRIDGE/scripts/build_qp_runtime_profile.sh $PROFILE${NC}"
    exit 1
  fi
  echo -e "${GREEN}✓ QP runtime ready: $QP_RUNTIME_ELF${NC}"
fi

echo -e "\n${YELLOW}[1/7] Ensuring TCP server...${NC}"
if probe_tcp_server; then
  echo -e "${GREEN}✓ Reusing TCP server on ${GVSOC_HOST}:${GVSOC_PORT}${NC}"
else
  echo "Starting TCP server (log: /tmp/tcp_generic.log)"
  GVSOC_SERVER_HOST="$GVSOC_BIND_HOST" \
  GVSOC_PORT="$GVSOC_PORT" \
  GVSOC_EXEC_MODE="$GVSOC_EXEC_MODE" \
  GVSOC_PERSISTENT_PATH="$GVSOC_PERSISTENT_PATH" \
  SHARC_OFFICIAL_RISCV_MODE="$SHARC_OFFICIAL_RISCV_MODE" \
  SHARC_DOUBLE_NATIVE="$SHARC_DOUBLE_NATIVE" \
  PULP_SDK_CONFIG="$PULP_SDK_CONFIG" \
  GVSOC_TARGET="$GVSOC_TARGET" \
  GVSOC_QP_PERSISTENT_BACKEND="$GVSOC_QP_PERSISTENT_BACKEND" \
  GVSOC_QP_PERSISTENT_EXPERIMENTAL="$GVSOC_QP_PERSISTENT_EXPERIMENTAL" \
  GVSOC_QP_PERSISTENT_ALLOW_FALLBACK="$GVSOC_QP_PERSISTENT_ALLOW_FALLBACK" \
  GVSOC_PERSISTENT_WORKERS="${GVSOC_PERSISTENT_WORKERS:-0}" \
    "$PYTHON_BIN" "$TCP_SERVER" > /tmp/tcp_generic.log 2>&1 &
  TCP_PID=$!
  echo "TCP PID: $TCP_PID"
  WAITED=0
  until probe_tcp_server; do
    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
    if [ $WAITED -ge 20 ]; then
      echo -e "\n${RED}ERROR: TCP server did not start within 20s${NC}"
      cat /tmp/tcp_generic.log || true
      exit 1
    fi
  done
  echo
  echo -e "${GREEN}✓ TCP server is ready${NC}"
fi

echo -e "\n${YELLOW}[2/7] Cleaning previous container with same name...${NC}"
docker rm -f "$SHARC_CONTAINER" 2>/dev/null || true
echo -e "${GREEN}✓ Clean${NC}"

echo -e "\n${YELLOW}[3/7] Running SHARC with ${CONFIG_NAME}...${NC}"
docker run \
  --name "$SHARC_CONTAINER" \
  --network=host \
  "${DOCKER_RUN_ARGS[@]}" \
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
 "$PYTHON_BIN" - "$OUT_DIR" "$CONFIG_HOST" <<'PYEOF'
import json
import os
import sys

out_dir = sys.argv[1]
config_path = sys.argv[2]

use_gvsoc = False
try:
    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    if isinstance(cfg, list):
        use_gvsoc = any(bool(item.get("use_gvsoc_controller")) for item in cfg if isinstance(item, dict))
    elif isinstance(cfg, dict):
        use_gvsoc = bool(cfg.get("use_gvsoc_controller"))
except Exception as exc:
    print(f"ERROR: Failed to read config for trace validation: {exc}")
    sys.exit(1)

if not use_gvsoc:
    print("Skipping trace validation (use_gvsoc_controller not enabled in config).")
    sys.exit(0)

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
OUT_DIR="$OUT_DIR" "$PYTHON_BIN" - <<'PYEOF'
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
