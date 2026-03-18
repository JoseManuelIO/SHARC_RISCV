#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
PROBE_SRC="${ROOT_DIR}/probes/eigen_probe.cpp"
HOST_BIN="${RESULTS_DIR}/eigen_probe_host"
CVA6_BIN="${RESULTS_DIR}/eigen_probe_cva6"
LOG_FILE="${RESULTS_DIR}/eigen_probe_build.log"
TARGET_DIR="${SDK_DIR}/buildroot/output/target"
INSTALL_DIR="${SDK_DIR}/install64"
TARGET_APP_NAME="plan_eigen_probe"

mkdir -p "${RESULTS_DIR}"

{
  echo "[Eigen Probe] start"
  echo "ROOT_DIR=${ROOT_DIR}"
  echo "SDK_DIR=${SDK_DIR}"

  EIGEN3_INCLUDE_DIR="${EIGEN3_INCLUDE_DIR:-${ROOT_DIR}/../deps/eigen}"
  echo "EIGEN3_INCLUDE_DIR=${EIGEN3_INCLUDE_DIR}"

  if [ ! -d "${EIGEN3_INCLUDE_DIR}" ]; then
    echo "ERROR: Eigen3 headers not found at ${EIGEN3_INCLUDE_DIR}"
    exit 2
  fi

  g++ -O2 -std=c++17 -I"${EIGEN3_INCLUDE_DIR}" "${PROBE_SRC}" -o "${HOST_BIN}"

  export PATH="${SDK_DIR}/buildroot/output/host/bin:${PATH}"
  CXX_CVA6="${CXX_CVA6:-riscv64-linux-cc}"
  echo "CXX_CVA6=${CXX_CVA6}"
  "${CXX_CVA6}" -x c++ -O2 -std=c++17 -I"${EIGEN3_INCLUDE_DIR}" "${PROBE_SRC}" -lstdc++ -lm -o "${CVA6_BIN}"

  mkdir -p "${TARGET_DIR}/usr/bin" /tmp/buildroot-ccache
  cp "${CVA6_BIN}" "${TARGET_DIR}/usr/bin/${TARGET_APP_NAME}"
  CCACHE_DIR=/tmp/buildroot-ccache make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)"
  cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${INSTALL_DIR}/vmlinux"
  (
    cd "${SDK_DIR}"
    CCACHE_DIR=/tmp/buildroot-ccache make spike_payload
  )

  file "${HOST_BIN}"
  file "${CVA6_BIN}"
  echo "TARGET_APP_NAME=${TARGET_APP_NAME}"
  echo "[Eigen Probe] build PASS"
} > "${LOG_FILE}" 2>&1

echo "Eigen probe build PASS"
