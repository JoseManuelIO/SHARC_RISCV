#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -x "./venv/bin/python" ]]; then
  PY="./venv/bin/python"
else
  PY="python3"
fi

echo "[T8] Full regeneration started"

"$PY" artifacts/T1_socket/validate_partition_spec.py
"$PY" artifacts/T1_socket/validate_backup_strategy.py
bash SHARCBRIDGE/scripts/bench_t1_tcp_baseline.sh
bash SHARCBRIDGE/scripts/bench_t2_socket_fastpath.sh

"$PY" SHARCBRIDGE/scripts/bench_t3_overhead_ab.py
"$PY" SHARCBRIDGE/scripts/bench_t5_pulp_kernels.py

bash SHARCBRIDGE/scripts/run_t6_hotspots.sh
bash SHARCBRIDGE/scripts/run_t6_incremental_ablation.sh
bash SHARCBRIDGE/scripts/run_t6_equivalence_gate.sh

bash SHARCBRIDGE/scripts/run_t7_load_campaign.sh
bash SHARCBRIDGE/scripts/run_t7_soak.sh
bash SHARCBRIDGE/scripts/run_t7_thesis_scenarios.sh

"$PY" artifacts/T8_socket/validate_academic_checklist.py

echo "[T8] Full regeneration completed"
