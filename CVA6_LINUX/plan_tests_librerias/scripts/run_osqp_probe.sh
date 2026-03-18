#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
HOST_OUT="${RESULTS_DIR}/osqp_probe_host.txt"
CVA6_OUT="${RESULTS_DIR}/osqp_probe_cva6.txt"
SPIKE_LOG="${RESULTS_DIR}/osqp_probe_spike.log"
STATUS_MD="${RESULTS_DIR}/osqp_probe_status.md"

mkdir -p "${RESULTS_DIR}"

bash "${ROOT_DIR}/scripts/build_osqp_probe.sh"
"${RESULTS_DIR}/osqp_probe_host" > "${HOST_OUT}"

python3 "${ROOT_DIR}/scripts/run_spike_noninteractive.py" \
  --spike "${SDK_DIR}/install64/bin/spike" \
  --payload "${SDK_DIR}/install64/spike_fw_payload.elf" \
  --command "plan_osqp_probe" \
  --expect "OSQP_PROBE_OK" \
  --log "${SPIKE_LOG}" \
  --boot-timeout 60 \
  --shutdown-timeout 20

awk '
  /OSQP_PROBE_OK/ {capture=1}
  capture {print}
  /y2=/ {if (capture) exit}
' "${SPIKE_LOG}" > "${CVA6_OUT}"

python3 - "${HOST_OUT}" "${CVA6_OUT}" > "${RESULTS_DIR}/osqp_probe_compare.txt" <<'PYEOF'
import math
import sys

def parse(path):
    vals = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k] = float(v)
    return vals

host = parse(sys.argv[1])
target = parse(sys.argv[2])
keys = ["status_val", "iter", "obj_val", "x0", "x1", "y0", "y1", "y2"]
tols = {
    "status_val": 0.0,
    "iter": 0.0,
    "obj_val": 1e-9,
    "x0": 1e-9,
    "x1": 1e-9,
    "y0": 1e-9,
    "y1": 1e-9,
    "y2": 1e-9,
}
failed = []
for key in keys:
    if key not in host or key not in target:
        failed.append(f"missing:{key}")
        continue
    diff = abs(host[key] - target[key])
    print(f"{key}: host={host[key]:.12f} target={target[key]:.12f} diff={diff:.3e}")
    if diff > tols[key]:
        failed.append(f"{key}:{diff}")
if failed:
    print("COMPARE_FAIL")
    sys.exit(3)
print("COMPARE_PASS")
PYEOF

{
  echo "# Tarea 3. OSQP Probe"
  echo
  echo "## Estado"
  echo
  echo "\`PASS\`"
  echo
  echo "## Evidencia"
  echo
  echo "- build log: \`${RESULTS_DIR}/osqp_probe_build.log\`"
  echo "- host output: \`${HOST_OUT}\`"
  echo "- spike log: \`${SPIKE_LOG}\`"
  echo "- cva6 output extraido: \`${CVA6_OUT}\`"
  echo "- comparacion: \`${RESULTS_DIR}/osqp_probe_compare.txt\`"
  echo
  echo "## Resultado"
  echo
  echo "OSQP v0.6.3 compila en host y en CVA6 Linux, ejecuta dentro de Spike y coincide numericamente con host."
} > "${STATUS_MD}"

echo "T3 OSQP probe PASS"
