#!/bin/bash
# Build MPC firmware with selectable numeric profile.
#
# Usage:
#   bash SHARCBRIDGE/scripts/build_mpc_profile.sh single
#   bash SHARCBRIDGE/scripts/build_mpc_profile.sh double
#
# Notes:
#   - double uses hard-double ISA/ABI (rv32imfdcxpulpv2/ilp32d).

set -euo pipefail

PROFILE="${1:-}"
if [ -z "$PROFILE" ]; then
  if [ "${SHARC_DOUBLE_NATIVE:-0}" = "1" ]; then
    PROFILE="double"
  else
    PROFILE="single"
  fi
fi

RISCV_TOOLCHAIN_PREFIX="${RISCV_TOOLCHAIN_PREFIX:-/opt/riscv}"
RISCV_GCC="${RISCV_GCC:-$RISCV_TOOLCHAIN_PREFIX/bin/riscv32-unknown-elf-gcc}"

case "$PROFILE" in
  single)
    MARCH="rv32imcxpulpv2"
    MABI="ilp32"
    ;;
  double)
    MARCH="rv32imfdcxpulpv2"
    MABI="ilp32d"
    if [ ! -x "$RISCV_GCC" ]; then
      echo "ERROR: GCC not found/executable: $RISCV_GCC"
      exit 2
    fi
    if ! "$RISCV_GCC" -print-multi-lib | grep -qi '@mabi=ilp32d'; then
      echo "ERROR: Active toolchain does not provide ilp32d multilib:"
      echo "  $RISCV_GCC"
      echo "Run: $RISCV_GCC -print-multi-lib"
      echo "Then install/select a toolchain with rv32* + ilp32d support."
      exit 2
    fi
    ;;
  *)
    echo "ERROR: profile must be 'single' or 'double', got '$PROFILE'"
    exit 1
    ;;
esac

echo "Building MPC profile=$PROFILE MARCH=$MARCH MABI=$MABI"
make -C SHARCBRIDGE/mpc clean all \
  SHARC_NUMERIC_PROFILE="$PROFILE" \
  MARCH="$MARCH" \
  MABI="$MABI"

echo "Done: SHARCBRIDGE/mpc/build/mpc_acc_controller.elf"
