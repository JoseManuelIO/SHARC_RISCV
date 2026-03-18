#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
LIBMPC_DIR="${ROOT_DIR}/../../sharc_original/libmpc"
EIGEN_DIR="${ROOT_DIR}/../deps/eigen"
OSQP_DIR="${ROOT_DIR}/../deps/osqp"
RESULTS_DIR="${ROOT_DIR}/results"
PROBE_SRC="${ROOT_DIR}/probes/libmpc_probe.cpp"
HOST_BIN="${RESULTS_DIR}/libmpc_probe_host"
CVA6_BIN="${RESULTS_DIR}/libmpc_probe_cva6"
LOG_FILE="${RESULTS_DIR}/libmpc_probe_build.log"
TARGET_DIR="${SDK_DIR}/buildroot/output/target"
INSTALL_DIR="${SDK_DIR}/install64"
TARGET_APP_NAME="plan_libmpc_probe"

mkdir -p "${RESULTS_DIR}"

{
  echo "[libmpc Probe] start"
  echo "ROOT_DIR=${ROOT_DIR}"
  echo "SDK_DIR=${SDK_DIR}"
  echo "LIBMPC_DIR=${LIBMPC_DIR}"
  echo "EIGEN_DIR=${EIGEN_DIR}"
  echo "OSQP_DIR=${OSQP_DIR}"

  test -d "${LIBMPC_DIR}/include"
  test -f "${OSQP_DIR}/build/out/libosqp.a"
  test -f "${OSQP_DIR}/build-cva6/out/libosqp.a"

  g++ -O2 -std=c++20 \
    -I"${LIBMPC_DIR}/include" \
    -I"${EIGEN_DIR}" \
    -I"${ROOT_DIR}/include_shims" \
    "${PROBE_SRC}" \
    "${OSQP_DIR}/build/out/libosqp.a" \
    -lm -lrt -ldl \
    -o "${HOST_BIN}"

  export PATH="${SDK_DIR}/buildroot/output/host/bin:${PATH}"
  riscv64-linux-g++ -O2 -std=c++20 \
    -I"${LIBMPC_DIR}/include" \
    -I"${EIGEN_DIR}" \
    -I"${ROOT_DIR}/include_shims" \
    "${PROBE_SRC}" \
    "${OSQP_DIR}/build-cva6/out/libosqp.a" \
    -lm -lrt -ldl \
    -o "${CVA6_BIN}"

  export CCACHE_DIR=/tmp/buildroot-ccache
  mkdir -p "${TARGET_DIR}/usr/bin" "${CCACHE_DIR}"
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
  echo "[libmpc Probe] build PASS"
} > "${LOG_FILE}" 2>&1

echo "libmpc probe build PASS"
