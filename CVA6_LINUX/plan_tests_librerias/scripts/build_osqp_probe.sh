#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
OSQP_DIR="${ROOT_DIR}/../deps/osqp"
RESULTS_DIR="${ROOT_DIR}/results"
PROBE_SRC="${ROOT_DIR}/probes/osqp_probe.c"
HOST_BIN="${RESULTS_DIR}/osqp_probe_host"
CVA6_BIN="${RESULTS_DIR}/osqp_probe_cva6"
LOG_FILE="${RESULTS_DIR}/osqp_probe_build.log"
HOST_BUILD_DIR="${OSQP_DIR}/build"
CVA6_BUILD_DIR="${OSQP_DIR}/build-cva6"
TARGET_DIR="${SDK_DIR}/buildroot/output/target"
INSTALL_DIR="${SDK_DIR}/install64"
TARGET_APP_NAME="plan_osqp_probe"

mkdir -p "${RESULTS_DIR}"

{
  echo "[OSQP Probe] start"
  echo "ROOT_DIR=${ROOT_DIR}"
  echo "SDK_DIR=${SDK_DIR}"
  echo "OSQP_DIR=${OSQP_DIR}"

  if [ ! -f "${OSQP_DIR}/include/osqp.h" ]; then
    echo "ERROR: osqp headers not found at ${OSQP_DIR}/include/osqp.h"
    exit 2
  fi

  if [ ! -f "${HOST_BUILD_DIR}/out/libosqp.a" ]; then
    echo "ERROR: host OSQP static library not found at ${HOST_BUILD_DIR}/out/libosqp.a"
    exit 3
  fi

  gcc -O2 -std=c99 \
    -I"${OSQP_DIR}/include" \
    "${PROBE_SRC}" \
    "${HOST_BUILD_DIR}/out/libosqp.a" \
    -lm -lrt -ldl \
    -o "${HOST_BIN}"

  export PATH="${SDK_DIR}/buildroot/output/host/bin:${PATH}"
  export CCACHE_DIR=/tmp/buildroot-ccache
  mkdir -p "${CCACHE_DIR}"

  mkdir -p "${CVA6_BUILD_DIR}"
  cmake -S "${OSQP_DIR}" -B "${CVA6_BUILD_DIR}" \
    -DUNITTESTS=OFF \
    -DBUILD_SHARED_LIBS=OFF \
    -DCMAKE_SYSTEM_NAME=Linux \
    -DCMAKE_C_COMPILER=riscv64-linux-gcc

  cmake --build "${CVA6_BUILD_DIR}" -j"$(nproc)"

  if [ ! -f "${CVA6_BUILD_DIR}/out/libosqp.a" ]; then
    echo "ERROR: CVA6 OSQP static library not found at ${CVA6_BUILD_DIR}/out/libosqp.a"
    exit 4
  fi

  riscv64-linux-gcc -O2 -std=c99 \
    -I"${OSQP_DIR}/include" \
    "${PROBE_SRC}" \
    "${CVA6_BUILD_DIR}/out/libosqp.a" \
    -lm -lrt -ldl \
    -o "${CVA6_BIN}"

  mkdir -p "${TARGET_DIR}/usr/bin"
  cp "${CVA6_BIN}" "${TARGET_DIR}/usr/bin/${TARGET_APP_NAME}"
  make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)"
  cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${INSTALL_DIR}/vmlinux"
  (
    cd "${SDK_DIR}"
    make spike_payload
  )

  file "${HOST_BIN}"
  file "${CVA6_BIN}"
  echo "TARGET_APP_NAME=${TARGET_APP_NAME}"
  echo "[OSQP Probe] build PASS"
} > "${LOG_FILE}" 2>&1

echo "OSQP probe build PASS"
