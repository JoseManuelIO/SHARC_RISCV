#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
TOOLCHAIN_BIN="${SDK_DIR}/buildroot/output/host/bin"
TARGET_DIR="${SDK_DIR}/buildroot/output/target"
INSTALL_DIR="${SDK_DIR}/install64"
RESULTS_DIR="${ROOT_DIR}/results"
APP_SRC="${ROOT_DIR}/cva6_app/hello_linux_smoke.c"
APP_BIN="${RESULTS_DIR}/hello_linux_smoke"
TARGET_APP_NAME="plan_hello_smoke"

mkdir -p "${RESULTS_DIR}" "${TARGET_DIR}/usr/bin" /tmp/buildroot-ccache

export PATH="${TOOLCHAIN_BIN}:${PATH}"

riscv64-linux-gcc "${APP_SRC}" -O2 -o "${APP_BIN}"
cp "${APP_BIN}" "${TARGET_DIR}/usr/bin/${TARGET_APP_NAME}"

CCACHE_DIR=/tmp/buildroot-ccache make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)"
cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${INSTALL_DIR}/vmlinux"
(
  cd "${SDK_DIR}"
  CCACHE_DIR=/tmp/buildroot-ccache make spike_payload
)

file "${APP_BIN}" > "${RESULTS_DIR}/hello_linux_smoke.file.txt"
printf '%s\n' "${INSTALL_DIR}/spike_fw_payload.elf" > "${RESULTS_DIR}/latest_payload.txt"

echo "Built smoke app and refreshed spike payload."
