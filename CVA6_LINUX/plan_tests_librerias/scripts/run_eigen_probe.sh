#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
HOST_OUT="${RESULTS_DIR}/eigen_probe_host.txt"
CVA6_OUT="${RESULTS_DIR}/eigen_probe_cva6.txt"
SPIKE_LOG="${RESULTS_DIR}/eigen_probe_spike.log"
STATUS_MD="${RESULTS_DIR}/eigen_probe_status.md"

mkdir -p "${RESULTS_DIR}"

bash "${ROOT_DIR}/scripts/build_eigen_probe.sh"
"${RESULTS_DIR}/eigen_probe_host" > "${HOST_OUT}"

python3 "${ROOT_DIR}/scripts/run_spike_noninteractive.py" \
  --spike "${SDK_DIR}/install64/bin/spike" \
  --payload "${SDK_DIR}/install64/spike_fw_payload.elf" \
  --command "plan_eigen_probe" \
  --expect "EIGEN_PROBE_OK" \
  --log "${SPIKE_LOG}" \
  --boot-timeout 60 \
  --shutdown-timeout 20

awk '
  /EIGEN_PROBE_OK/ {capture=1}
  capture {print}
  /checksum=/ {if (capture) exit}
' "${SPIKE_LOG}" > "${CVA6_OUT}"

python3 - "${HOST_OUT}" "${CVA6_OUT}" > "${RESULTS_DIR}/eigen_probe_compare.txt" <<'PYEOF'
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
keys = ["x0", "x1", "x2", "checksum"]
tol = 1e-9
failed = []
for key in keys:
    if key not in host or key not in target:
        failed.append(f"missing:{key}")
        continue
    diff = abs(host[key] - target[key])
    print(f"{key}: host={host[key]:.12f} target={target[key]:.12f} diff={diff:.3e}")
    if diff > tol:
        failed.append(f"{key}:{diff}")
if failed:
    print("COMPARE_FAIL")
    sys.exit(3)
print("COMPARE_PASS")
PYEOF

{
  echo "# Tarea 2. Eigen Probe"
  echo
  echo "## Estado"
  echo
  echo "\`PASS\`"
  echo
  echo "## Evidencia"
  echo
  echo "- build log: \`${RESULTS_DIR}/eigen_probe_build.log\`"
  echo "- host output: \`${HOST_OUT}\`"
  echo "- spike log: \`${SPIKE_LOG}\`"
  echo "- cva6 output extraido: \`${CVA6_OUT}\`"
  echo "- comparacion: \`${RESULTS_DIR}/eigen_probe_compare.txt\`"
  echo
  echo "## Resultado"
  echo
  echo "Eigen compila en host y en CVA6 Linux, ejecuta dentro de Spike y coincide numericamente con host dentro de tolerancia."
} > "${STATUS_MD}"

echo "T2 Eigen probe PASS"
