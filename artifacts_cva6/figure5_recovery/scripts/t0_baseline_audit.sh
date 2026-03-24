#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECOVERY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARTIFACTS_DIR="$(cd "${RECOVERY_DIR}/.." && pwd)"
REPO_DIR="$(cd "${ARTIFACTS_DIR}/.." && pwd)"
RESULTS_DIR="${RECOVERY_DIR}/results"

mkdir -p "${RESULTS_DIR}"

STATUS_OUT="${RESULTS_DIR}/t0_nested_repos_status.txt"
ARTIFACTS_OUT="${RESULTS_DIR}/t0_artifact_inventory.txt"
REPORT_OUT="${RESULTS_DIR}/t0_baseline_audit.md"

MAIN_HEAD="$(git -C "${REPO_DIR}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
SDK_HEAD="$(git -C "${REPO_DIR}/CVA6_LINUX/cva6-sdk" rev-parse --short HEAD 2>/dev/null || echo unknown)"
CVA6_HEAD="$(git -C "${REPO_DIR}/CVA6_LINUX/cva6" rev-parse --short HEAD 2>/dev/null || echo unknown)"

{
  echo "# T0 Nested Repo Status"
  echo
  echo "date=$(date -Iseconds)"
  echo "repo_head=${MAIN_HEAD}"
  echo "cva6_sdk_head=${SDK_HEAD}"
  echo "cva6_head=${CVA6_HEAD}"
  echo
  echo "## repo git status --short"
  git -C "${REPO_DIR}" status --short || true
  echo
  echo "## cva6-sdk git status --short"
  git -C "${REPO_DIR}/CVA6_LINUX/cva6-sdk" status --short || true
  echo
  echo "## cva6 git status --short"
  git -C "${REPO_DIR}/CVA6_LINUX/cva6" status --short || true
} > "${STATUS_OUT}"

{
  echo "# T0 Artifact Inventory"
  echo
  echo "date=$(date -Iseconds)"
  echo
  echo "## known_good_docs"
  printf '%s\n' \
    "${REPO_DIR}/artifacts_cva6/figure5_t9_run_summary.md" \
    "${REPO_DIR}/artifacts_cva6/spike_hw_metrics_validation.md" \
    "${REPO_DIR}/artifacts_cva6/t4_rootfs_manifest.txt"
  echo
  echo "## current_runtime_logs"
  printf '%s\n' \
    "/tmp/sharcbridge_cva6_runtime/persistent_session.log" \
    "/tmp/sharcbridge_cva6_runtime/0.log" \
    "/tmp/sharcbridge_cva6_runtime/task3-run0.log"
  echo
  echo "## tracked_install64"
  ls -l "${REPO_DIR}/install64/vmlinux" "${REPO_DIR}/install64/Image" 2>/dev/null || true
  file "${REPO_DIR}/install64/vmlinux" "${REPO_DIR}/install64/Image" 2>/dev/null || true
  echo
  echo "## sdk_install64"
  ls -l \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf" \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/vmlinux" \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/bin/sharc_cva6_acc_runtime" \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json" \
    2>/dev/null || true
  file \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf" \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/install64/vmlinux" \
    "${REPO_DIR}/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/bin/sharc_cva6_acc_runtime" \
    2>/dev/null || true
  echo
  echo "## latest_figure5_runs"
  ls -1 /tmp/sharc_cva6_figure5 2>/dev/null | tail -n 20 || true
} > "${ARTIFACTS_OUT}"

{
  echo "# T0 Baseline Audit"
  echo
  echo "- date: \`$(date -Iseconds)\`"
  echo "- repo_head: \`${MAIN_HEAD}\`"
  echo "- cva6_sdk_head: \`${SDK_HEAD}\`"
  echo "- cva6_head: \`${CVA6_HEAD}\`"
  echo
  echo "## Known Good Reference"
  echo
  echo "- main evidence: \`artifacts_cva6/figure5_t9_run_summary.md\`"
  echo "- secondary evidence: \`artifacts_cva6/spike_hw_metrics_validation.md\`"
  echo "- rootfs staging evidence: \`artifacts_cva6/t4_rootfs_manifest.txt\`"
  echo
  echo "## Outputs"
  echo
  echo "- nested status: \`${STATUS_OUT}\`"
  echo "- artifact inventory: \`${ARTIFACTS_OUT}\`"
} > "${REPORT_OUT}"

echo "PASS t0_baseline_audit"
echo "report=${REPORT_OUT}"
echo "status=${STATUS_OUT}"
echo "artifacts=${ARTIFACTS_OUT}"
