#!/bin/bash
# run_gvsoc_config_double.sh
#
# Convenience launcher for double profile:
# - Builds MPC in double profile (ilp32d)
# - Runs existing generic config launcher with SHARC_DOUBLE_NATIVE=1
#
# Usage:
#   source venv/bin/activate
#   bash SHARCBRIDGE/scripts/run_gvsoc_config_double.sh gvsoc_test.json

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <config_filename.json>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export SHARC_DOUBLE_NATIVE=1

# Build hard-double profile (rv32imfdcxpulpv2/ilp32d).
bash "$SCRIPT_DIR/build_mpc_profile.sh" double
bash "$SCRIPT_DIR/run_gvsoc_config.sh" "$@"
