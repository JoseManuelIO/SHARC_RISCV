#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECOVERY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARTIFACTS_DIR="$(cd "${RECOVERY_DIR}/.." && pwd)"
REPO_DIR="$(cd "${ARTIFACTS_DIR}/.." && pwd)"
RESULTS_DIR="${RECOVERY_DIR}/results"
LOGS_DIR="${RECOVERY_DIR}/logs"

mkdir -p "${RESULTS_DIR}" "${LOGS_DIR}"

BEFORE_MANIFEST="${RESULTS_DIR}/c7_before_manifest.txt"
AFTER_MANIFEST="${RESULTS_DIR}/c7_after_manifest.txt"
ROOTFS_BEFORE="${RESULTS_DIR}/c7_rootfs_before.txt"
ROOTFS_AFTER="${RESULTS_DIR}/c7_rootfs_after.txt"
DIFF_MANIFEST="${RESULTS_DIR}/c7_manifest_diff.txt"
BUILD_LOG="${LOGS_DIR}/c7_controlled_guest_rebuild.log"

FILES=(
  "SHARCBRIDGE_CVA6/build/cva6_acc_runtime"
  "CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/bin/sharc_cva6_acc_runtime"
  "CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json"
  "CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio"
  "CVA6_LINUX/cva6-sdk/install64/vmlinux"
  "CVA6_LINUX/cva6-sdk/install64/Image"
  "CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf"
)

capture_manifest() {
  local out="$1"
  : > "${out}"
  (
    cd "${REPO_DIR}"
    for f in "${FILES[@]}"; do
      if [ -e "${f}" ]; then
        echo "FILE ${f}"
        sha256sum "${f}"
        stat -c 'STAT|%n|%s|%y' "${f}"
        file "${f}" 2>/dev/null || true
        echo
      else
        echo "MISSING ${f}"
        echo
      fi
    done
  ) >> "${out}"
}

capture_rootfs_listing() {
  local out="$1"
  (
    cd "${REPO_DIR}"
    if [ -e "CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio" ]; then
      cpio -it < "CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio" \
        | rg '(^usr/bin/sharc_cva6_acc_runtime$|^usr/share/sharcbridge_cva6/base_config.json$|^lib/ld-linux-riscv64-lp64d.so.1$)' || true
    fi
  ) > "${out}"
}

capture_manifest "${BEFORE_MANIFEST}"
capture_rootfs_listing "${ROOTFS_BEFORE}"

(
  cd "${REPO_DIR}"
  bash "SHARCBRIDGE_CVA6/cva6_image_builder.sh"
) > "${BUILD_LOG}" 2>&1

capture_manifest "${AFTER_MANIFEST}"
capture_rootfs_listing "${ROOTFS_AFTER}"

diff -u "${BEFORE_MANIFEST}" "${AFTER_MANIFEST}" > "${DIFF_MANIFEST}" || true

echo "c7 controlled guest rebuild complete"
echo "build_log=${BUILD_LOG}"
echo "before_manifest=${BEFORE_MANIFEST}"
echo "after_manifest=${AFTER_MANIFEST}"
echo "manifest_diff=${DIFF_MANIFEST}"
