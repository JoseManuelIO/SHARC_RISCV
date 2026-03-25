#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${REPO_DIR}/venv/bin/python3"
if [ -x "${VENV_PY}" ]; then
  PYTHON_BIN="${VENV_PY}"
else
  PYTHON_BIN="python3"
fi

CONFIG_NAME="${1:-cva6_figure5.json}"
CONFIG_HOST="${SCRIPT_DIR}/${CONFIG_NAME}"
CONFIG_DOCKER="/home/dcuser/examples/acc_example/simulation_configs/${CONFIG_NAME}"
WRAPPER_HOST="${SCRIPT_DIR}/cva6_controller_wrapper.py"
TCP_SERVER="${SCRIPT_DIR}/cva6_tcp_server.py"
IMAGE_BUILDER="${SCRIPT_DIR}/cva6_image_builder.sh"
KNOWN_GOOD_SDK_DIR="${CVA6_KNOWN_GOOD_SDK_DIR:-/tmp/cva6-sdk-clean-20260324-r1-2}"
REPO_SDK_DIR="${REPO_DIR}/CVA6_LINUX/cva6-sdk"

resolve_default_sdk_dir() {
  if [ -n "${CVA6_SDK_DIR:-}" ]; then
    echo "${CVA6_SDK_DIR}"
    return 0
  fi

  if [ -d "${KNOWN_GOOD_SDK_DIR}" ]; then
    echo "${KNOWN_GOOD_SDK_DIR}"
    return 0
  fi

  echo "${REPO_SDK_DIR}"
}

CVA6_HOST="${CVA6_HOST:-127.0.0.1}"
CVA6_PORT="${CVA6_PORT:-5001}"
CVA6_BIND_HOST="${CVA6_BIND_HOST:-0.0.0.0}"
CVA6_RUNTIME_MODE="${CVA6_RUNTIME_MODE:-spike_persistent}"
CVA6_SDK_DIR="$(resolve_default_sdk_dir)"
CVA6_SKIP_BUILD="${CVA6_SKIP_BUILD:-}"
if [ -z "${CVA6_SKIP_BUILD}" ]; then
  if [ "${CVA6_SDK_DIR}" = "${KNOWN_GOOD_SDK_DIR}" ]; then
    CVA6_SKIP_BUILD="1"
  else
    CVA6_SKIP_BUILD="0"
  fi
fi
CVA6_REQUEST_EXEC_TIMEOUT_S="${CVA6_REQUEST_EXEC_TIMEOUT_S:-${CVA6_SPIKE_TIMEOUT_S:-300}}"
if [ -n "${CVA6_SOCKET_TIMEOUT_S:-}" ]; then
  CVA6_SOCKET_TIMEOUT_S="${CVA6_SOCKET_TIMEOUT_S}"
else
  CVA6_SOCKET_TIMEOUT_S="$(${PYTHON_BIN} - "${CVA6_REQUEST_EXEC_TIMEOUT_S}" <<'PYEOF'
import sys
try:
    base = float(sys.argv[1])
except Exception:
    base = 300.0
print(f"{base + 30.0:.1f}")
PYEOF
)"
fi
SHARC_CVA6_OFFICIAL_MODE="${SHARC_CVA6_OFFICIAL_MODE:-1}"
TIMESTAMP="$(date +%Y-%m-%d--%H-%M-%S)"
OUT_DIR="/tmp/sharc_cva6_figure5/${TIMESTAMP}-${CONFIG_NAME%.json}"
SHARC_CONTAINER="sharc_cva6_figure5_main"
TCP_PID=""
DOCKER_ENV_ARGS=()

if [ -n "${CVA6_CHIP_CYCLE_NS:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "CVA6_CHIP_CYCLE_NS=${CVA6_CHIP_CYCLE_NS}")
  DOCKER_ENV_ARGS+=(-e "GVSOC_CHIP_CYCLE_NS=${CVA6_CHIP_CYCLE_NS}")
elif [ -n "${GVSOC_CHIP_CYCLE_NS:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "GVSOC_CHIP_CYCLE_NS=${GVSOC_CHIP_CYCLE_NS}")
  DOCKER_ENV_ARGS+=(-e "CVA6_CHIP_CYCLE_NS=${GVSOC_CHIP_CYCLE_NS}")
fi

resolve_effective_spike_bin() {
  if [ -n "${CVA6_SPIKE_BIN:-}" ]; then
    echo "${CVA6_SPIKE_BIN}"
    return 0
  fi

  if [ -n "${CVA6_SDK_DIR:-}" ] && [ -x "${CVA6_SDK_DIR}/install64/bin/spike" ]; then
    echo "${CVA6_SDK_DIR}/install64/bin/spike"
    return 0
  fi

  if [ -x "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/bin/spike" ]; then
    echo "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/bin/spike"
    return 0
  fi

  return 1
}

resolve_effective_spike_payload() {
  if [ -n "${CVA6_SPIKE_PAYLOAD:-}" ]; then
    echo "${CVA6_SPIKE_PAYLOAD}"
    return 0
  fi

  if [ -n "${CVA6_SDK_DIR:-}" ]; then
    echo "${CVA6_SDK_DIR}/install64/spike_fw_payload.elf"
    return 0
  fi

  echo "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf"
}

probe_tcp_server() {
  "${PYTHON_BIN}" - "${CVA6_HOST}" "${CVA6_PORT}" <<'PYEOF'
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
try:
    with socket.create_connection((host, port), timeout=1.0) as sock:
        sock.settimeout(1.0)
        sock.sendall((json.dumps({"type": "health", "request_id": "probe"}) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    if not data:
        raise RuntimeError("no response")
    msg = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
    if msg.get("status") == "OK":
        sys.exit(0)
    raise RuntimeError(f"unexpected response: {msg}")
except Exception:
    sys.exit(1)
PYEOF
}

probe_tcp_server_health() {
  "${PYTHON_BIN}" - "${CVA6_HOST}" "${CVA6_PORT}" <<'PYEOF'
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
try:
  with socket.create_connection((host, port), timeout=1.0) as sock:
    sock.settimeout(1.0)
    sock.sendall((json.dumps({"type": "health", "request_id": "probe-mode"}) + "\n").encode("utf-8"))
    data = b""
    while b"\n" not in data:
      chunk = sock.recv(4096)
      if not chunk:
        break
      data += chunk
  if not data:
    raise RuntimeError("no response")
  msg = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
  if msg.get("status") != "OK":
    raise RuntimeError(f"unexpected response: {msg}")
  print(json.dumps(msg, sort_keys=True))
except Exception:
  sys.exit(1)
PYEOF
}

shutdown_tcp_server() {
  "${PYTHON_BIN}" - "${CVA6_HOST}" "${CVA6_PORT}" <<'PYEOF'
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
try:
    with socket.create_connection((host, port), timeout=1.0) as sock:
        sock.sendall((json.dumps({"type": "shutdown"}) + "\n").encode("utf-8"))
except Exception:
    pass
PYEOF
}

cleanup() {
  local status=$?
  docker rm -f "${SHARC_CONTAINER}" 2>/dev/null || true
  if [ -n "${TCP_PID}" ] && kill -0 "${TCP_PID}" 2>/dev/null; then
    shutdown_tcp_server || true
    sleep 0.3
    kill "${TCP_PID}" 2>/dev/null || true
  fi
  exit ${status}
}
trap cleanup EXIT INT TERM

if [ ! -f "${CONFIG_HOST}" ]; then
  echo "ERROR: Missing config ${CONFIG_HOST}"
  exit 1
fi

mkdir -p "${OUT_DIR}" "${OUT_DIR}/latest"

if [ "${CVA6_RUNTIME_MODE}" = "spike" ] || [ "${CVA6_RUNTIME_MODE}" = "spike_persistent" ]; then
  export CVA6_SDK_DIR
  if RESOLVED_SPIKE_BIN="$(resolve_effective_spike_bin)"; then
    export CVA6_SPIKE_BIN="${RESOLVED_SPIKE_BIN}"
  fi
  export CVA6_SPIKE_PAYLOAD="$(resolve_effective_spike_payload)"
fi

echo "=== SHARC + CVA6 Figure 5 over TCP ==="
echo "OUT_DIR=${OUT_DIR}"
echo "CONFIG=${CONFIG_HOST}"
echo "CVA6 backend=${CVA6_HOST}:${CVA6_PORT} mode=${CVA6_RUNTIME_MODE}"
echo "CVA6 sdk dir=${CVA6_SDK_DIR}"
echo "CVA6 wrapper socket timeout=${CVA6_SOCKET_TIMEOUT_S}s"
echo "CVA6 request exec timeout=${CVA6_REQUEST_EXEC_TIMEOUT_S}s"
if [ -n "${CVA6_SPIKE_BIN:-}" ]; then
  echo "CVA6 spike bin=${CVA6_SPIKE_BIN}"
fi
if [ -n "${CVA6_SPIKE_PAYLOAD:-}" ]; then
  echo "CVA6 spike payload=${CVA6_SPIKE_PAYLOAD}"
fi

EXPERIMENT_COUNT="$("${PYTHON_BIN}" - "${CONFIG_HOST}" <<'PYEOF'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(len(data))
PYEOF
)"
if [ "${EXPERIMENT_COUNT}" -ne 2 ]; then
  echo "ERROR: Expected 2 experiments in ${CONFIG_HOST}, got ${EXPERIMENT_COUNT}"
  exit 1
fi

if [ "${CVA6_SKIP_BUILD}" != "1" ]; then
  echo "[1/6] Building CVA6 payload"
  if ! bash "${IMAGE_BUILDER}" > "${OUT_DIR}/image_build.log" 2>&1; then
    echo "ERROR: cva6_image_builder.sh failed"
    tail -n 200 "${OUT_DIR}/image_build.log" || true
    exit 1
  fi
else
  echo "[1/6] Skipping build (CVA6_SKIP_BUILD=1)"
fi

echo "[2/6] Starting or reusing CVA6 TCP server"
if probe_tcp_server; then
  CURRENT_HEALTH="$(probe_tcp_server_health || echo '{}')"
  REUSE_CHECK="$("${PYTHON_BIN}" - "${CURRENT_HEALTH}" "${CVA6_RUNTIME_MODE}" "${CVA6_SDK_DIR:-}" "${CVA6_SPIKE_BIN:-}" "${CVA6_SPIKE_PAYLOAD:-}" <<'PYEOF'
import json
import sys
from pathlib import Path

health = json.loads(sys.argv[1])
expected_mode = sys.argv[2]
expected_sdk = sys.argv[3]
expected_spike_bin = sys.argv[4]
expected_payload = sys.argv[5]

def norm(value: str) -> str:
    if not value:
        return ""
    return str(Path(value).expanduser().resolve(strict=False))

checks = {
    "runtime_mode": (str(health.get("runtime_mode", "")), expected_mode),
    "sdk_dir": (norm(str(health.get("sdk_dir", ""))), norm(expected_sdk)),
    "spike_bin": (norm(str(health.get("spike_bin", ""))), norm(expected_spike_bin)),
    "spike_payload": (norm(str(health.get("spike_payload", ""))), norm(expected_payload)),
}

mismatches = []
for key, (actual, expected) in checks.items():
    if expected and actual != expected:
        mismatches.append(f"{key}: actual={actual or '<empty>'} expected={expected}")

if mismatches:
    print("RESTART")
    for line in mismatches:
        print(line)
else:
    print("REUSE")
PYEOF
)"
  REUSE_DECISION="$(printf '%s\n' "${REUSE_CHECK}" | sed -n '1p')"
  if [ "${REUSE_DECISION}" = "REUSE" ]; then
    echo "Reusing TCP server on ${CVA6_HOST}:${CVA6_PORT}"
  else
    echo "Restarting TCP server because health identity does not match current request"
    printf '%s\n' "${REUSE_CHECK}" | sed -n '2,$p'
    shutdown_tcp_server || true
    sleep 0.5
    CVA6_SERVER_HOST="${CVA6_BIND_HOST}" \
    CVA6_SERVER_PORT="${CVA6_PORT}" \
    CVA6_RUNTIME_MODE="${CVA6_RUNTIME_MODE}" \
    CVA6_REQUEST_EXEC_TIMEOUT_S="${CVA6_REQUEST_EXEC_TIMEOUT_S}" \
    "${PYTHON_BIN}" "${TCP_SERVER}" > "${OUT_DIR}/tcp_server.log" 2>&1 &
    TCP_PID=$!
    waited=0
    until probe_tcp_server; do
      sleep 1
      waited=$((waited + 1))
      if [ ${waited} -ge 20 ]; then
        echo "ERROR: CVA6 TCP server did not restart"
        cat "${OUT_DIR}/tcp_server.log" || true
        exit 1
      fi
    done
  fi
else
  CVA6_SERVER_HOST="${CVA6_BIND_HOST}" \
  CVA6_SERVER_PORT="${CVA6_PORT}" \
  CVA6_RUNTIME_MODE="${CVA6_RUNTIME_MODE}" \
  CVA6_REQUEST_EXEC_TIMEOUT_S="${CVA6_REQUEST_EXEC_TIMEOUT_S}" \
  "${PYTHON_BIN}" "${TCP_SERVER}" > "${OUT_DIR}/tcp_server.log" 2>&1 &
  TCP_PID=$!
  waited=0
  until probe_tcp_server; do
    sleep 1
    waited=$((waited + 1))
    if [ ${waited} -ge 20 ]; then
      echo "ERROR: CVA6 TCP server did not start"
      cat "${OUT_DIR}/tcp_server.log" || true
      exit 1
    fi
  done
fi

echo "[3/6] Running SHARC Figure 5 config"
docker rm -f "${SHARC_CONTAINER}" 2>/dev/null || true
docker run \
  --name "${SHARC_CONTAINER}" \
  --network=host \
  -e "CVA6_TRANSPORT=tcp" \
  -e "CVA6_HOST=${CVA6_HOST}" \
  -e "CVA6_PORT=${CVA6_PORT}" \
  -e "CVA6_SOCKET_TIMEOUT_S=${CVA6_SOCKET_TIMEOUT_S}" \
  -e "SHARC_CVA6_OFFICIAL_MODE=${SHARC_CVA6_OFFICIAL_MODE}" \
  "${DOCKER_ENV_ARGS[@]}" \
  -v "${OUT_DIR}:/home/dcuser/examples/acc_example/experiments" \
  -v "${WRAPPER_HOST}:/home/dcuser/examples/acc_example/gvsoc_controller_wrapper_v2.py" \
  -v "${CONFIG_HOST}:${CONFIG_DOCKER}:ro" \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  sharc --config_filename "${CONFIG_NAME}" \
  > "${OUT_DIR}/sharc_figure5.log" 2>&1

echo "[4/6] Checking outputs"
DATA_COUNT=$(find "${OUT_DIR}" -name "simulation_data_incremental.json" | wc -l | tr -d ' ')
if [ "${DATA_COUNT}" -lt 2 ]; then
  echo "ERROR: Expected at least 2 simulation_data_incremental.json outputs, got ${DATA_COUNT}"
  find "${OUT_DIR}" -name "simulation_data_incremental.json" -print || true
  exit 1
fi

echo "[5/6] Building latest experiment bundle"
OUT_DIR="${OUT_DIR}" "${PYTHON_BIN}" - <<'PYEOF'
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
    data[label] = {
        "label": label,
        "experiment directory": "/home/dcuser/examples/acc_example/latest",
        "experiment data": exp_data,
        "experiment config": cfg,
    }

output_json = os.path.join(latest_dir, "experiment_list_data_incremental.json")
with open(output_json, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
print(output_json)
PYEOF

echo "[6/6] Generating plots"
docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "${OUT_DIR}:/home/dcuser/examples/acc_example/experiments" \
  -v "${OUT_DIR}/latest:/home/dcuser/examples/acc_example/latest" \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  python3 generate_example_figures.py \
  > "${OUT_DIR}/plot_generation.log" 2>&1

echo "OUT_DIR=${OUT_DIR}"
echo "PLOT=${OUT_DIR}/latest/plots.png"
