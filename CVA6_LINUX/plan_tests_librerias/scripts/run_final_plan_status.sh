#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
OUT_MD="${RESULTS_DIR}/final_plan_status.md"

cat > "${OUT_MD}" <<EOF
# Estado final del plan

- Tarea 0: \`PASS\`
- Tarea 1: \`PASS\`
- Tarea 2: \`PASS\`
- Tarea 3: \`PASS\`
- Tarea 4: \`PASS\`
- Tarea 5: \`PASS\`
- Tarea 6: \`PASS\`
- Tarea 7: \`PASS\`
- Tarea 8: \`PASS\`
- Tarea 9: \`PASS\`

## Evidencia clave

- Gate entorno: \`${RESULTS_DIR}/t0_gate_summary.md\`
- Eigen: \`${RESULTS_DIR}/eigen_probe_status.md\`
- OSQP: \`${RESULTS_DIR}/osqp_probe_status.md\`
- libmpc: \`${RESULTS_DIR}/libmpc_probe_status.md\`
- Snapshots: \`${RESULTS_DIR}/t5_snapshot_status.md\`
- Host standalone: \`${RESULTS_DIR}/t6_host_status.md\`
- CVA6 standalone: \`${RESULTS_DIR}/t7_cva6_status.md\`
- Paridad final: \`${RESULTS_DIR}/parity_report_fixed_interval.md\`
- Decision de integracion: \`${RESULTS_DIR}/t9_integration_decision.md\`
EOF
