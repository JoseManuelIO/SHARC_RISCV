#!/bin/bash
# run_gvsoc_figure5_tcp.sh
#
# Reproduce Figure 5 over TCP transport:
#   1. GVSoC - Real Delays (wrapper -> TCP server)
#   2. Baseline - No Delay (Onestep)
#
# Usage:
#   cd ~/Repositorios/SHARC_RISCV
#   source venv/bin/activate
#   bash SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh

set -euo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARCBRIDGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$SHARCBRIDGE_DIR/.." && pwd)"

WRAPPER_HOST="$SHARCBRIDGE_DIR/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py"
TCP_SERVER="$SCRIPT_DIR/gvsoc_tcp_server.py"
VENV_ACTIVATE="$REPO_DIR/venv/bin/activate"
BUILD_MPC_SCRIPT="$SCRIPT_DIR/build_mpc_profile.sh"
BUILD_QP_SCRIPT="$SCRIPT_DIR/build_qp_runtime_profile.sh"
QP_RUNTIME_ELF="$SHARCBRIDGE_DIR/mpc/build/qp_riscv_runtime.elf"
CONFIG_DOCKER="/home/dcuser/examples/acc_example/simulation_configs/gvsoc_figure5.json"
CONFIG_HOST="$REPO_DIR/sharc_original/examples/acc_example/simulation_configs/gvsoc_figure5.json"

GVSOC_HOST="${GVSOC_HOST:-127.0.0.1}"
GVSOC_PORT="${GVSOC_PORT:-5001}"
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
TIMESTAMP=$(date +%Y-%m-%d--%H-%M-%S)
EXP_DIR="/tmp/sharc_figure5_tcp/$TIMESTAMP"
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

# ── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TCP_PID=""
SHARC_CONTAINER="sharc_figure5_main"

probe_tcp_server() {
    python3 - "$GVSOC_HOST" "$GVSOC_PORT" <<'PYEOF'
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
    python3 - "$GVSOC_HOST" "$GVSOC_PORT" <<'PYEOF'
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

# ── Cleanup ───────────────────────────────────────────────────────────────────
cleanup() {
    local exit_code=$?
    echo -e "\n${YELLOW}[Cleanup] Stopping containers and server...${NC}"
    docker rm -f "$SHARC_CONTAINER" sharc_figure5_wrapper 2>/dev/null || true
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
echo -e "${CYAN}║   SHARC + GVSoC: Figure 5 over TCP                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "   Output dir: $EXP_DIR"
echo -e "   Config: $CONFIG_HOST"
echo -e "   Transport: tcp (${GVSOC_HOST}:${GVSOC_PORT})"
echo -e "   TCP bind: ${GVSOC_BIND_HOST}:${GVSOC_PORT}"
echo -e "   Exec mode: ${GVSOC_EXEC_MODE}"
echo -e "   Persistent path: ${GVSOC_PERSISTENT_PATH}"
echo -e "   Official RISC-V mode: ${SHARC_OFFICIAL_RISCV_MODE}"
echo -e "   Double mode: ${SHARC_DOUBLE_NATIVE}"
echo -e "   SDK cfg: ${PULP_SDK_CONFIG}"
echo -e "   Target: ${GVSOC_TARGET}"
if [ -n "${GVSOC_CHIP_CYCLE_NS:-}" ]; then
    echo -e "   Cycle ns: ${GVSOC_CHIP_CYCLE_NS} (from env)"
fi
if [ -n "${GVSOC_QP_SOLVE:-}" ]; then
    echo -e "   QP solve mode: ${GVSOC_QP_SOLVE}"
fi
if [ -n "${GVSOC_QP_PERSISTENT_BACKEND:-}" ]; then
    echo -e "   QP backend: ${GVSOC_QP_PERSISTENT_BACKEND}"
fi
if [ -n "${GVSOC_QP_PERSISTENT_EXPERIMENTAL:-}" ]; then
    echo -e "   QP experimental: ${GVSOC_QP_PERSISTENT_EXPERIMENTAL}"
fi
if [ -n "${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK:-}" ]; then
    echo -e "   QP allow fallback: ${GVSOC_QP_PERSISTENT_ALLOW_FALLBACK}"
fi

# ── Step 1: Activate venv ─────────────────────────────────────────────────────
echo -e "\n${YELLOW}[1/7] Activating venv...${NC}"
# shellcheck source=/dev/null
source "$VENV_ACTIVATE"
echo -e "${GREEN}✓ Python environment ready${NC}"

echo -e "\n${YELLOW}[1b/7] Building MPC profile...${NC}"
if [ "${SHARC_SKIP_BUILD:-0}" = "1" ]; then
    echo -e "${YELLOW}Skipping build (SHARC_SKIP_BUILD=1)${NC}"
else
    if [ "${GVSOC_QP_SOLVE:-0}" = "1" ]; then
        if [ "$SHARC_DOUBLE_NATIVE" = "1" ]; then
            bash "$BUILD_QP_SCRIPT" double
        else
            bash "$BUILD_QP_SCRIPT" single
        fi
        if [ ! -f "$QP_RUNTIME_ELF" ]; then
            echo -e "${RED}ERROR: Missing QP runtime ELF after build: $QP_RUNTIME_ELF${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ QP runtime build completed${NC}"
    elif [ "$SHARC_DOUBLE_NATIVE" = "1" ]; then
        bash "$BUILD_MPC_SCRIPT" double
        echo -e "${GREEN}✓ MPC build completed${NC}"
    else
        bash "$BUILD_MPC_SCRIPT" single
        echo -e "${GREEN}✓ MPC build completed${NC}"
    fi
fi

# ── Step 2: Check config and wrapper ─────────────────────────────────────────
echo -e "\n${YELLOW}[2/7] Checking config and wrapper...${NC}"

if [ ! -f "$CONFIG_HOST" ]; then
    echo -e "${RED}ERROR: Config not found: $CONFIG_HOST${NC}"
    exit 1
fi

EXPERIMENT_COUNT=$(python3 -c "
import json
with open('$CONFIG_HOST') as f:
    d = json.load(f)
print(len(d))
")
echo "   Config has $EXPERIMENT_COUNT experiments"
if [ "$EXPERIMENT_COUNT" -ne 2 ]; then
    echo -e "${RED}ERROR: Expected 2 experiments in $CONFIG_HOST, got $EXPERIMENT_COUNT${NC}"
    exit 1
fi

if ! grep -q "GVSoCTCPClient" "$WRAPPER_HOST"; then
    echo -e "${RED}ERROR: Wrapper does not have GVSoCTCPClient: $WRAPPER_HOST${NC}"
    exit 1
fi
if ! grep -q "GVSOC_TRANSPORT" "$WRAPPER_HOST"; then
    echo -e "${RED}ERROR: Wrapper does not expose GVSOC_TRANSPORT selector: $WRAPPER_HOST${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Config OK (2 experiments), wrapper TCP selector OK${NC}"

# ── Step 3: Start TCP server ─────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/7] Starting TCP server on ${GVSOC_HOST}:${GVSOC_PORT}...${NC}"
if probe_tcp_server; then
    echo -e "${GREEN}✓ Compatible TCP server already running — reusing it${NC}"
    TCP_PID=""
else
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
        python3 "$TCP_SERVER" > /tmp/tcp_figure5.log 2>&1 &
    TCP_PID=$!
    echo "   TCP server PID: $TCP_PID (logs: /tmp/tcp_figure5.log)"

    WAITED=0
    until probe_tcp_server; do
        sleep 1
        WAITED=$((WAITED + 1))
        echo -n "."
        if [ "$WAITED" -ge 20 ]; then
            echo -e "\n${RED}ERROR: TCP server did not start within 20s${NC}"
            cat /tmp/tcp_figure5.log || true
            exit 1
        fi
    done
    echo -e "\n${GREEN}✓ TCP server ready at ${GVSOC_HOST}:${GVSOC_PORT}${NC}"
fi

# ── Step 4: Clean workspace ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/7] Preparing experiment workspace...${NC}"
docker rm -f "$SHARC_CONTAINER" sharc_figure5_wrapper 2>/dev/null || true
rm -rf "$EXP_DIR"
mkdir -p "$EXP_DIR"
echo -e "${GREEN}✓ Clean workspace: $EXP_DIR${NC}"

# ── Step 5: Start SHARC with gvsoc_figure5.json ─────────────────────────────
echo -e "\n${YELLOW}[5/7] Starting SHARC (gvsoc_figure5.json, 2 experiments)...${NC}"
echo "   Note: SHARC runs both experiments sequentially inside the container."
echo "         The wrapper is forced to TCP transport via env vars."

docker run \
    --name "$SHARC_CONTAINER" \
    --network=host \
    "${DOCKER_ENV_ARGS[@]}" \
    -v "$EXP_DIR:/home/dcuser/examples/acc_example/experiments" \
    -v "$WRAPPER_HOST:/home/dcuser/examples/acc_example/gvsoc_controller_wrapper_v2.py" \
    -v "$CONFIG_HOST:$CONFIG_DOCKER:ro" \
    -w /home/dcuser/examples/acc_example \
    sharc-gvsoc:latest \
    sharc --config_filename gvsoc_figure5.json

SHARC_EXIT=$?
if [ $SHARC_EXIT -ne 0 ]; then
    echo -e "${RED}ERROR: SHARC execution failed with code $SHARC_EXIT${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SHARC container finished (name: $SHARC_CONTAINER)${NC}"

# ── Step 6: Verify results ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[6/7] Verifying results...${NC}"

DATA_FILES=$(find "$EXP_DIR" -name "simulation_data_incremental.json" 2>/dev/null | sort)
DATA_COUNT=$(echo "$DATA_FILES" | grep -c "simulation_data_incremental" || true)

echo "   Found $DATA_COUNT simulation_data_incremental.json files"
echo "$DATA_FILES"

python3 - "$EXP_DIR" <<'PYEOF'
import json
import os
import sys

exp_dir = sys.argv[1]
data_files = []
for root, _dirs, files in os.walk(exp_dir):
    for name in files:
        if name == 'simulation_data_incremental.json':
            data_files.append(os.path.join(root, name))

data_files.sort()

if len(data_files) < 1:
    print(f"ERROR: No simulation_data_incremental.json found in {exp_dir}")
    sys.exit(1)

print(f"\n  Found {len(data_files)} experiment output(s):")
for path in data_files:
    with open(path) as f:
        d = json.load(f)
    x = d.get('x', [])
    t = d.get('t', [])
    n = len(t)
    relpath = os.path.relpath(path, exp_dir)
    print(f"\n  [{relpath}]")
    print(f"    n_samples: {n}")
    print(f"    x[0]:  {x[0] if x else 'N/A'}")
    print(f"    x[-1]: {x[-1] if x else 'N/A'}")
    assert n >= 5, f"Too few time steps: {n}"
    assert 'x' in d and 'u' in d and 't' in d, "Missing x/u/t"
    print("    ✓ valid structure")

print(f"\n  ✓ All {len(data_files)} experiment(s) have valid output")
PYEOF

# ── Step 7: Generate plots ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[7/7] Preparing plot input and running generate_example_figures.py...${NC}"
mkdir -p "$EXP_DIR/latest"
EXP_DIR="$EXP_DIR" python3 - <<'PYEOF'
import glob
import json
import os

exp_dir = os.path.abspath(os.environ['EXP_DIR'])
out_dir = os.path.join(exp_dir, 'latest')
os.makedirs(out_dir, exist_ok=True)
data = {}
for path in sorted(glob.glob(os.path.join(exp_dir, '**', 'simulation_data_incremental.json'), recursive=True)):
    with open(path) as fh:
        sim = json.load(fh)
    cfg_path = os.path.join(os.path.dirname(path), 'config.json')
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    exp_data = {k: sim.get(k, []) for k in ('k', 't', 'x', 'u', 'w')}
    exp_data['pending_computations'] = sim.get('pending_computation', sim.get('pending_computations', []))
    exp_data['batches'] = sim.get('batches', None)
    label = os.path.basename(os.path.dirname(path)) or os.path.basename(path)
    key = label
    i = 1
    while key in data:
        key = f"{label}_{i}"
        i += 1
    data[key] = {
        'label': label,
        'experiment directory': '/home/dcuser/examples/acc_example/latest',
        'experiment data': exp_data,
        'experiment config': cfg,
    }
with open(os.path.join(out_dir, 'experiment_list_data_incremental.json'), 'w') as fh:
    json.dump(data, fh, indent=2)
print('Wrote', os.path.join(out_dir, 'experiment_list_data_incremental.json'))
PYEOF

docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "${EXP_DIR}:/home/dcuser/examples/acc_example/experiments" \
  -v "${EXP_DIR}/latest:/home/dcuser/examples/acc_example/latest" \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  python3 generate_example_figures.py

PLOTS_PNG="$EXP_DIR/latest/plots.png"
if [ -f "$PLOTS_PNG" ]; then
    echo -e "${GREEN}✓ Plots generated: $PLOTS_PNG${NC}"
else
    echo -e "${RED}ERROR: plots.png not found in $EXP_DIR/latest${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[7b/7] Collecting hardware metrics table and plot...${NC}"
python3 "$SCRIPT_DIR/collect_run_hw_metrics.py" --run-dir "$EXP_DIR"
if [ ! -f "$EXP_DIR/latest/hw_metrics.png" ]; then
    echo -e "${YELLOW}Host matplotlib unavailable, generating HW plot inside Docker...${NC}"
    docker run --rm \
        -u "$(id -u):$(id -g)" \
        -v "$REPO_DIR:/repo" \
        -v "$EXP_DIR:/run" \
        -w /repo \
        sharc-gvsoc:latest \
        python3 SHARCBRIDGE/scripts/t8_generate_hw_plot.py \
            --hw-csv /run/latest/hw_metrics.csv \
            --out-plot /run/latest/hw_metrics.png
fi
echo -e "${GREEN}✓ Hardware metrics exported to $EXP_DIR/latest/hw_metrics.*${NC}"

echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✓ FIGURE 5 TCP COMPLETE                                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "${GREEN}   Results: $EXP_DIR${NC}"
echo -e "${GREEN}   TCP logs: /tmp/tcp_figure5.log${NC}"
