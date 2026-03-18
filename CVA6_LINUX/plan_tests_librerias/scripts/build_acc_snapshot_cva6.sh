#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
LIBMPC_DIR="${ROOT_DIR}/../../sharc_original/libmpc"
CTRL_INCLUDE_DIR="${ROOT_DIR}/../../sharc_original/resources/controllers/include"
CTRL_SRC_DIR="${ROOT_DIR}/../../sharc_original/resources/controllers/src"
RES_INCLUDE_DIR="${ROOT_DIR}/../../sharc_original/resources/include"
EIGEN_DIR="${ROOT_DIR}/../deps/eigen"
OSQP_DIR="${ROOT_DIR}/../deps/osqp"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
OUT_BIN="${RESULTS_DIR}/acc_snapshot_cva6"
LOG_FILE="${RESULTS_DIR}/t7_build_cva6.log"
TARGET_SHARE_DIR="${SDK_DIR}/buildroot/output/target/usr/share/plan_tests_librerias"
TARGET_SNAP_DIR="${TARGET_SHARE_DIR}/snapshots"
TARGET_BIN_DIR="${SDK_DIR}/buildroot/output/target/usr/bin"
INSTALL_DIR="${SDK_DIR}/install64"

mkdir -p "${RESULTS_DIR}"

{
  echo "[T7 cva6 build] start"
  export PATH="${SDK_DIR}/buildroot/output/host/bin:${PATH}"
  export CCACHE_DIR=/tmp/buildroot-ccache
  mkdir -p "${CCACHE_DIR}"

  riscv64-linux-g++ -O2 -std=c++20 \
    -DTNX=3 -DTNU=2 -DTNDU=2 -DTNY=1 \
    -DPREDICTION_HORIZON=5 -DCONTROL_HORIZON=5 \
    -I"${CTRL_INCLUDE_DIR}" \
    -I"${RES_INCLUDE_DIR}" \
    -I"${LIBMPC_DIR}/include" \
    -I"${EIGEN_DIR}" \
    -I"${ROOT_DIR}/include_shims" \
    "${ROOT_DIR}/host_ref/acc_snapshot_host.cpp" \
    "${CTRL_SRC_DIR}/controller.cpp" \
    "${CTRL_SRC_DIR}/ACC_Controller.cpp" \
    "${OSQP_DIR}/build-cva6/out/libosqp.a" \
    -lm -lrt -ldl \
    -o "${OUT_BIN}"

  mkdir -p "${TARGET_SNAP_DIR}" "${TARGET_BIN_DIR}"
  cp "${OUT_BIN}" "${TARGET_BIN_DIR}/plan_acc_snapshot_cva6"
  cp "${ROOT_DIR}/../../sharc_original/examples/acc_example/base_config.json" "${TARGET_SHARE_DIR}/base_config.json"
  cp "${ROOT_DIR}/snapshots"/snapshot_*.json "${TARGET_SNAP_DIR}/"

  cat > "${TARGET_BIN_DIR}/plan_acc_snapshot_batch.sh" <<'SHEOF'
#!/bin/sh
set -e
CFG=/usr/share/plan_tests_librerias/base_config.json
BIN=/usr/bin/plan_acc_snapshot_cva6
for s in /usr/share/plan_tests_librerias/snapshots/snapshot_*.json; do
  base=$(basename "$s" .json)
  echo "SNAP_BEGIN:${base}"
  "$BIN" "$CFG" "$s"
  echo "SNAP_END:${base}"
done
echo "T7_BATCH_DONE"
SHEOF
  chmod +x "${TARGET_BIN_DIR}/plan_acc_snapshot_batch.sh"

  make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)"
  cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${INSTALL_DIR}/vmlinux"
  (
    cd "${SDK_DIR}"
    make spike_payload
  )

  file "${OUT_BIN}"
  echo "[T7 cva6 build] PASS"
} > "${LOG_FILE}" 2>&1

echo "T7 cva6 build PASS"
