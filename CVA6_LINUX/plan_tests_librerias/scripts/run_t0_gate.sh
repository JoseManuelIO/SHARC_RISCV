#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
LOG_PATH="${RESULTS_DIR}/t0_spike_smoke.log"
SUMMARY_PATH="${RESULTS_DIR}/t0_gate_summary.md"

mkdir -p "${RESULTS_DIR}"

{
  echo "# Tarea 0 Gate"
  echo
  echo "## Verificaciones"
  echo
  test -x /opt/riscv64-unknown-elf/bin/riscv64-unknown-elf-gcc && echo "- baremetal toolchain: PASS" || echo "- baremetal toolchain: FAIL"
  test -x "${SDK_DIR}/buildroot/output/host/bin/riscv64-linux-gcc" && echo "- linux toolchain: PASS" || echo "- linux toolchain: FAIL"
  test -x "${SDK_DIR}/install64/bin/spike" && echo "- spike: PASS" || echo "- spike: FAIL"
} > "${SUMMARY_PATH}"

"${ROOT_DIR}/scripts/build_linux_smoke.sh"

python3 "${ROOT_DIR}/scripts/run_spike_noninteractive.py" \
  --spike "${SDK_DIR}/install64/bin/spike" \
  --payload "${SDK_DIR}/install64/spike_fw_payload.elf" \
  --command "plan_hello_smoke" \
  --expect "PLAN_LIBS_SMOKE_OK" \
  --log "${LOG_PATH}"

{
  echo
  echo "## Resultado"
  echo
  echo "- smoke app Linux en Spike: PASS"
  echo "- log: \`${LOG_PATH}\`"
  echo "- payload: \`${SDK_DIR}/install64/spike_fw_payload.elf\`"
} >> "${SUMMARY_PATH}"

echo "T0 gate PASS"
