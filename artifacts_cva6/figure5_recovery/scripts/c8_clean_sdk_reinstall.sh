#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECOVERY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARTIFACTS_DIR="$(cd "${RECOVERY_DIR}/.." && pwd)"
REPO_DIR="$(cd "${ARTIFACTS_DIR}/.." && pwd)"
RESULTS_DIR="${RECOVERY_DIR}/results"
LOGS_DIR="${RECOVERY_DIR}/logs"
BACKUP_DIR="${RESULTS_DIR}/c8_backup_before_reinstall"

mkdir -p "${RESULTS_DIR}" "${LOGS_DIR}" "${BACKUP_DIR}"

LOG_FILE="${LOGS_DIR}/c8_clean_sdk_reinstall.log"
PRE_MANIFEST="${RESULTS_DIR}/c8_pre_reinstall_manifest.txt"
POST_MANIFEST="${RESULTS_DIR}/c8_post_reinstall_manifest.txt"
DIFF_MANIFEST="${RESULTS_DIR}/c8_reinstall_manifest_diff.txt"

FILES=(
  "install64/vmlinux"
  "install64/Image"
  "install64/spike_fw_payload.elf"
  "CVA6_LINUX/cva6-sdk/install64/vmlinux"
  "CVA6_LINUX/cva6-sdk/install64/Image"
  "CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf"
  "CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio"
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

(
  cd "${REPO_DIR}"
  cp "install64/vmlinux" "${BACKUP_DIR}/vmlinux"
  cp "install64/Image" "${BACKUP_DIR}/Image"
  cp "install64/spike_fw_payload.elf" "${BACKUP_DIR}/spike_fw_payload.elf"
) 2>/dev/null || true

capture_manifest "${PRE_MANIFEST}"

(
  cd "${REPO_DIR}"
  echo "=== make -C CVA6_LINUX/cva6-sdk clean ==="
  make -C "CVA6_LINUX/cva6-sdk" clean
  echo "=== make -C CVA6_LINUX/cva6-sdk gcc ==="
  make -C "CVA6_LINUX/cva6-sdk" gcc
  echo "=== bash SHARCBRIDGE_CVA6/cva6_image_builder.sh ==="
  bash "SHARCBRIDGE_CVA6/cva6_image_builder.sh"
) > "${LOG_FILE}" 2>&1

capture_manifest "${POST_MANIFEST}"
diff -u "${PRE_MANIFEST}" "${POST_MANIFEST}" > "${DIFF_MANIFEST}" || true

echo "c8 clean sdk reinstall complete"
echo "log_file=${LOG_FILE}"
echo "backup_dir=${BACKUP_DIR}"
