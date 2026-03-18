#!/bin/bash
# Final one-command verification for official SHARC_RISCV path.
# Includes pipeline, repeatability and fidelity gates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

if [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi

echo "[1/4] verify_official_pipeline.sh"
bash SHARCBRIDGE/scripts/verify_official_pipeline.sh

echo "[2/4] check_official_repeatability.sh"
bash SHARCBRIDGE/scripts/check_official_repeatability.sh

echo "[3/4] t3_formulation_parity_gate.py"
python3 SHARCBRIDGE/scripts/t3_formulation_parity_gate.py \
  --tol 1e-12 \
  --report-json artifacts/T3_formulation_parity_gate_latest.json \
  --report-md artifacts/T3_formulation_parity_gate_latest.md

echo "[4/4] t8_fidelity_gate.py"
python3 SHARCBRIDGE/scripts/t8_fidelity_gate.py \
  --thresholds artifacts/T8_fidelity_thresholds_v1.json \
  --report-json artifacts/T8_fidelity_gate_latest.json \
  --report-md artifacts/T8_fidelity_gate_latest.md

echo "PASS: final official verification complete"
