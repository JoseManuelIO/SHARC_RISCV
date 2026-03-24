#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECOVERY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARTIFACTS_DIR="$(cd "${RECOVERY_DIR}/.." && pwd)"
REPO_DIR="$(cd "${ARTIFACTS_DIR}/.." && pwd)"
RESULTS_DIR="${RECOVERY_DIR}/results"
LOGS_DIR="${RECOVERY_DIR}/logs"
WORK_DIR="${RESULTS_DIR}/c9_forensic_triplet"
GOOD_DIR="${WORK_DIR}/good_reference"
REGEN_DIR="${WORK_DIR}/regenerated_current"
META_DIR="${WORK_DIR}/metadata"

mkdir -p "${RESULTS_DIR}" "${LOGS_DIR}" "${GOOD_DIR}" "${REGEN_DIR}" "${META_DIR}"

BUILD_LOG="${LOGS_DIR}/c9_forensic_triplet_rebuild.log"
SUMMARY_TXT="${META_DIR}/summary.txt"

GOOD_FILES=(
  "install64/vmlinux"
  "install64/Image"
  "install64/spike_fw_payload.elf"
)

copy_triplet() {
  local dest="$1"
  mkdir -p "${dest}"
  cp "${REPO_DIR}/install64/vmlinux" "${dest}/vmlinux"
  cp "${REPO_DIR}/install64/Image" "${dest}/Image"
  cp "${REPO_DIR}/install64/spike_fw_payload.elf" "${dest}/spike_fw_payload.elf"
}

capture_meta() {
  local prefix="$1"
  local dir="$2"
  : > "${META_DIR}/${prefix}_sha256.txt"
  : > "${META_DIR}/${prefix}_stat.txt"
  : > "${META_DIR}/${prefix}_file.txt"
  for f in vmlinux Image spike_fw_payload.elf; do
    sha256sum "${dir}/${f}" >> "${META_DIR}/${prefix}_sha256.txt"
    stat -c '%n|%s|%y' "${dir}/${f}" >> "${META_DIR}/${prefix}_stat.txt"
    file "${dir}/${f}" >> "${META_DIR}/${prefix}_file.txt"
    readelf -h "${dir}/${f}" > "${META_DIR}/${prefix}_${f}.readelf_header.txt" 2>&1 || true
    readelf -n "${dir}/${f}" > "${META_DIR}/${prefix}_${f}.readelf_notes.txt" 2>&1 || true
    readelf -l "${dir}/${f}" > "${META_DIR}/${prefix}_${f}.readelf_program_headers.txt" 2>&1 || true
  done
}

copy_triplet "${GOOD_DIR}"
capture_meta "good" "${GOOD_DIR}"

GOOD_ROOTFS_HASH="$(sha256sum "${REPO_DIR}/CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio" | awk '{print $1}')"
printf 'good_reference_rootfs_current_hash=%s\n' "${GOOD_ROOTFS_HASH}" > "${SUMMARY_TXT}"

(
  cd "${REPO_DIR}"
  bash "SHARCBRIDGE_CVA6/cva6_image_builder.sh"
) > "${BUILD_LOG}" 2>&1

cp "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/vmlinux" "${REGEN_DIR}/vmlinux"
cp "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/Image" "${REGEN_DIR}/Image"
cp "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf" "${REGEN_DIR}/spike_fw_payload.elf"
cp "${REPO_DIR}/CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio" "${REGEN_DIR}/rootfs.cpio"

capture_meta "regenerated" "${REGEN_DIR}"
sha256sum "${REGEN_DIR}/rootfs.cpio" > "${META_DIR}/regenerated_rootfs_sha256.txt"
stat -c '%n|%s|%y' "${REGEN_DIR}/rootfs.cpio" > "${META_DIR}/regenerated_rootfs_stat.txt"
cpio -it < "${REGEN_DIR}/rootfs.cpio" | rg '(^usr/bin/sharc_cva6_acc_runtime$|^usr/share/sharcbridge_cva6/base_config.json$|^lib/ld-linux-riscv64-lp64d.so.1$)' > "${META_DIR}/regenerated_rootfs_listing.txt" || true

diff -u "${META_DIR}/good_sha256.txt" "${META_DIR}/regenerated_sha256.txt" > "${META_DIR}/triplet_sha256.diff" || true
diff -u "${META_DIR}/good_stat.txt" "${META_DIR}/regenerated_stat.txt" > "${META_DIR}/triplet_stat.diff" || true
diff -u "${META_DIR}/good_file.txt" "${META_DIR}/regenerated_file.txt" > "${META_DIR}/triplet_file.diff" || true
for f in vmlinux Image spike_fw_payload.elf; do
  diff -u "${META_DIR}/good_${f}.readelf_header.txt" "${META_DIR}/regenerated_${f}.readelf_header.txt" > "${META_DIR}/${f}.readelf_header.diff" || true
  diff -u "${META_DIR}/good_${f}.readelf_notes.txt" "${META_DIR}/regenerated_${f}.readelf_notes.txt" > "${META_DIR}/${f}.readelf_notes.diff" || true
  diff -u "${META_DIR}/good_${f}.readelf_program_headers.txt" "${META_DIR}/regenerated_${f}.readelf_program_headers.txt" > "${META_DIR}/${f}.readelf_program_headers.diff" || true
done

# Restore known bootable reference triplet after comparison.
cp "${GOOD_DIR}/vmlinux" "${REPO_DIR}/install64/vmlinux"
cp "${GOOD_DIR}/Image" "${REPO_DIR}/install64/Image"
cp "${GOOD_DIR}/spike_fw_payload.elf" "${REPO_DIR}/install64/spike_fw_payload.elf"
cp "${GOOD_DIR}/vmlinux" "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/vmlinux"
cp "${GOOD_DIR}/Image" "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/Image"
cp "${GOOD_DIR}/spike_fw_payload.elf" "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf"

{
  echo "c9 forensic triplet compare complete"
  echo "build_log=${BUILD_LOG}"
  echo "good_dir=${GOOD_DIR}"
  echo "regenerated_dir=${REGEN_DIR}"
} >> "${SUMMARY_TXT}"

echo "c9 forensic triplet compare complete"
echo "build_log=${BUILD_LOG}"
echo "good_dir=${GOOD_DIR}"
echo "regenerated_dir=${REGEN_DIR}"
