#!/bin/bash
# One-command verification for official TCP+double SHARCBRIDGE pipeline.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

if [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi

echo "[1/6] Build MPC (double)"
bash SHARCBRIDGE/scripts/build_mpc_profile.sh double

echo "[2/6] Check ilp32d multilib"
/opt/riscv/bin/riscv32-unknown-elf-gcc -print-multi-lib | grep -i 'ilp32d'

echo "[3/6] GVSoC ELF smoke"
SHARC_DOUBLE_NATIVE=1 SHARC_DOUBLE_STRICT=1 python3 SHARCBRIDGE/scripts/smoke_gvsoc_elf_run.py

echo "[4/6] Official pytest suite"
bash SHARCBRIDGE/scripts/run_official_pytest_suite.sh

echo "[5/6] E2E short run (gvsoc_test.json)"
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_config.sh gvsoc_test.json

echo "[6/6] Figure 5 TCP run with HW metrics"
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh

echo "PASS: official pipeline verification complete"
