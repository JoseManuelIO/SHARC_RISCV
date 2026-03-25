#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
MATRIX_JSON="${1:-${REPO_DIR}/artifacts_cva6/cache_sweep/configs/cache_sweep_matrix_smoke.json}"
RUNNER="${REPO_DIR}/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh"
RESULTS_DIR="${REPO_DIR}/artifacts_cva6/cache_sweep/results"
MANIFEST_JSON="${RESULTS_DIR}/cache_sweep_manifest.json"
VENV_PY="${REPO_DIR}/venv/bin/python3"
KNOWN_GOOD_SDK_DIR="${CVA6_KNOWN_GOOD_SDK_DIR:-/tmp/cva6-sdk-clean-20260324-r1-2}"
BASE_PORT="${CACHE_SWEEP_BASE_PORT:-5040}"
RUNTIME_MODE="${CVA6_RUNTIME_MODE:-spike_persistent}"
SKIP_BUILD="${CVA6_SKIP_BUILD:-1}"
SHELL_READY_ATTEMPTS="${CVA6_SPIKE_SHELL_READY_ATTEMPTS:-10}"
SHELL_PROMPT_TIMEOUT_S="${CVA6_SPIKE_SHELL_PROMPT_TIMEOUT_S:-30}"
SHELL_MARKER_TIMEOUT_S="${CVA6_SPIKE_SHELL_MARKER_TIMEOUT_S:-60}"
BOOT_TIMEOUT_S="${CVA6_SPIKE_BOOT_TIMEOUT_S:-300}"
READY_TIMEOUT_S="${CVA6_SPIKE_READY_TIMEOUT_S:-420}"
SPIKE_TIMEOUT_S="${CVA6_SPIKE_TIMEOUT_S:-900}"

if [ -x "${VENV_PY}" ]; then
  PYTHON_BIN="${VENV_PY}"
else
  PYTHON_BIN="python3"
fi

mkdir -p "${RESULTS_DIR}"

if [ ! -f "${MATRIX_JSON}" ]; then
  echo "ERROR: Missing matrix ${MATRIX_JSON}" >&2
  exit 1
fi

if [ ! -x "${RUNNER}" ]; then
  echo "ERROR: Missing runner ${RUNNER}" >&2
  exit 1
fi

TMP_CASES="$(mktemp)"
cleanup() {
  rm -f "${TMP_CASES}"
}
trap cleanup EXIT

"${PYTHON_BIN}" - "${MATRIX_JSON}" > "${TMP_CASES}" <<'PYEOF'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

for entry in data:
    print(json.dumps(entry, sort_keys=True))
PYEOF

"${PYTHON_BIN}" - "${TMP_CASES}" "${MANIFEST_JSON}" "${BASE_PORT}" "${KNOWN_GOOD_SDK_DIR}" "${RUNTIME_MODE}" "${SKIP_BUILD}" <<'PYEOF'
import json
import sys
from pathlib import Path

cases_path = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
base_port = int(sys.argv[3])
sdk_dir = sys.argv[4]
runtime_mode = sys.argv[5]
skip_build = sys.argv[6]
cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
manifest = {
    "matrix_source": str(cases_path),
    "base_port": base_port,
    "sdk_dir": sdk_dir,
    "runtime_mode": runtime_mode,
    "skip_build": skip_build,
    "runs": [],
    "cases": cases,
}
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PYEOF

CASE_INDEX=0
while IFS= read -r case_json; do
  [ -n "${case_json}" ] || continue

  CASE_ID="$("${PYTHON_BIN}" - "${case_json}" <<'PYEOF'
import json
import sys
print(json.loads(sys.argv[1])["id"])
PYEOF
)"
  CASE_LABEL="$("${PYTHON_BIN}" - "${case_json}" <<'PYEOF'
import json
import sys
print(json.loads(sys.argv[1])["label"])
PYEOF
)"
  CACHE_ARGS="$("${PYTHON_BIN}" - "${case_json}" <<'PYEOF'
import json
import sys
print(json.loads(sys.argv[1]).get("spike_cache_args", ""))
PYEOF
)"

  CASE_PORT=$((BASE_PORT + CASE_INDEX))
  LOG_PATH="${RESULTS_DIR}/${CASE_ID}.log"

  echo "=== Running case ${CASE_ID}: ${CASE_LABEL} ==="
  echo "CVA6_PORT=${CASE_PORT}"
  echo "SPIKE_CACHE_ARGS=${CACHE_ARGS}"

  if ! \
    CVA6_PORT="${CASE_PORT}" \
    CVA6_SKIP_BUILD="${SKIP_BUILD}" \
    CVA6_RUNTIME_MODE="${RUNTIME_MODE}" \
    CVA6_SDK_DIR="${KNOWN_GOOD_SDK_DIR}" \
    CVA6_SPIKE_BOOT_TIMEOUT_S="${BOOT_TIMEOUT_S}" \
    CVA6_SPIKE_READY_TIMEOUT_S="${READY_TIMEOUT_S}" \
    CVA6_SPIKE_TIMEOUT_S="${SPIKE_TIMEOUT_S}" \
    CVA6_SPIKE_SHELL_READY_ATTEMPTS="${SHELL_READY_ATTEMPTS}" \
    CVA6_SPIKE_SHELL_PROMPT_TIMEOUT_S="${SHELL_PROMPT_TIMEOUT_S}" \
    CVA6_SPIKE_SHELL_MARKER_TIMEOUT_S="${SHELL_MARKER_TIMEOUT_S}" \
    SPIKE_CACHE_ARGS="${CACHE_ARGS}" \
    bash "${RUNNER}" > "${LOG_PATH}" 2>&1; then
    echo "ERROR: runner failed for ${CASE_ID}. See ${LOG_PATH}" >&2
    exit 1
  fi

  OUT_DIR="$("${PYTHON_BIN}" - "${LOG_PATH}" <<'PYEOF'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
matches = re.findall(r"^OUT_DIR=(.+)$", text, flags=re.MULTILINE)
print(matches[-1] if matches else "")
PYEOF
)"

  "${PYTHON_BIN}" - "${MANIFEST_JSON}" "${case_json}" "${LOG_PATH}" "${OUT_DIR}" "${CASE_PORT}" <<'PYEOF'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
case = json.loads(sys.argv[2])
log_path = sys.argv[3]
out_dir = sys.argv[4]
case_port = int(sys.argv[5])

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["runs"].append(
    {
        "id": case["id"],
        "label": case["label"],
        "port": case_port,
        "spike_cache_args": case.get("spike_cache_args", ""),
        "log_path": log_path,
        "out_dir": out_dir,
    }
)
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PYEOF
  CASE_INDEX=$((CASE_INDEX + 1))
done < "${TMP_CASES}"

echo "Manifest: ${MANIFEST_JSON}"
