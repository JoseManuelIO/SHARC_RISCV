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

CVA6_HOST="${CVA6_HOST:-127.0.0.1}"
CVA6_PORT="${CVA6_PORT:-5001}"
CVA6_RUNTIME_MODE="${CVA6_RUNTIME_MODE:-spike}"
RUN_BASE="${CVA6_RUN_BASE:-/tmp/sharc_cva6_runs}"
TIMESTAMP="$(date +%Y-%m-%d--%H-%M-%S)"
RUN_DIR="${RUN_BASE}/${TIMESTAMP}-cva6_short"
SERVER_LOG="${RUN_DIR}/server.log"
WRAPPER_LOG="${RUN_DIR}/wrapper.log"
RESULT_JSON="${RUN_DIR}/result.json"
SNAPSHOT_JSON="${RUN_DIR}/snapshot.json"
TCP_PID=""

mkdir -p "${RUN_DIR}"

shutdown_server() {
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
  if [ -n "${TCP_PID}" ] && kill -0 "${TCP_PID}" 2>/dev/null; then
    shutdown_server || true
    sleep 0.2
    kill "${TCP_PID}" 2>/dev/null || true
  fi
  exit ${status}
}
trap cleanup EXIT INT TERM

if [ $# -ge 1 ]; then
  cp "$1" "${SNAPSHOT_JSON}"
else
  cat > "${SNAPSHOT_JSON}" <<'EOF'
{"request_id":"t5-short","k":0,"t":0.0,"x":[0.0,100.0,20.0],"w":[22.0,0.0],"u_prev":[0.0,0.0]}
EOF
fi

mkdir -p "${RUN_DIR}/sim"

"${PYTHON_BIN}" - "${SNAPSHOT_JSON}" "${RUN_DIR}/sim" <<'PYEOF'
import json
import sys
from pathlib import Path

snap = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
sim = Path(sys.argv[2])
sim.mkdir(parents=True, exist_ok=True)

def write(name: str, text: str) -> None:
    (sim / name).write_text(text, encoding="utf-8")

write("k_py_to_c++", f"{int(snap['k'])}\nEND OF PIPE\n")
write("t_py_to_c++", f"{float(snap['t'])}\nEND OF PIPE\n")
write("x_py_to_c++", "[" + ", ".join(str(float(v)) for v in snap["x"]) + "]\nEND OF PIPE\n")
write("w_py_to_c++", "[" + ", ".join(str(float(v)) for v in snap["w"]) + "]\nEND OF PIPE\n")
write("t_delay_py_to_c++", "0\nEND OF PIPE\n")
PYEOF

CVA6_RUNTIME_MODE="${CVA6_RUNTIME_MODE}" \
CVA6_SERVER_HOST="${CVA6_HOST}" \
CVA6_SERVER_PORT="${CVA6_PORT}" \
"${PYTHON_BIN}" "${SCRIPT_DIR}/cva6_tcp_server.py" > "${SERVER_LOG}" 2>&1 &
TCP_PID=$!

"${PYTHON_BIN}" - "${CVA6_HOST}" "${CVA6_PORT}" <<'PYEOF'
import json
import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])

deadline = time.time() + 20.0
last_error = "server did not respond"
while time.time() < deadline:
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
                raise RuntimeError("empty response")
            msg = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
            if msg.get("status") == "OK":
                sys.exit(0)
            last_error = f"unexpected health response: {msg}"
    except Exception as exc:
        last_error = str(exc)
    time.sleep(0.5)

raise SystemExit(last_error)
PYEOF

CVA6_TRANSPORT=tcp \
CVA6_HOST="${CVA6_HOST}" \
CVA6_PORT="${CVA6_PORT}" \
"${PYTHON_BIN}" "${SCRIPT_DIR}/cva6_controller_wrapper.py" "${RUN_DIR}/sim" > "${WRAPPER_LOG}" 2>&1

"${PYTHON_BIN}" - "${RUN_DIR}/sim" "${SNAPSHOT_JSON}" "${RESULT_JSON}" <<'PYEOF'
import json
import sys
from pathlib import Path

sim = Path(sys.argv[1])
snap = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
u_line = (sim / "u_c++_to_py").read_text(encoding="utf-8").splitlines()[0]
meta_line = (sim / "metadata_c++_to_py").read_text(encoding="utf-8").splitlines()[0]
u = json.loads(u_line)
metadata = json.loads(meta_line)
out = {
    "snapshot": snap,
    "u": u,
    "metadata": metadata,
    "trace_file": str(sim / "cva6_wrapper_trace.ndjson"),
}
Path(sys.argv[3]).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(out, indent=2, sort_keys=True))
PYEOF

echo "RUN_DIR=${RUN_DIR}"
echo "RESULT_JSON=${RESULT_JSON}"
