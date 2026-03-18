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
OUT_BIN="${RESULTS_DIR}/acc_snapshot_host"
LOG_FILE="${RESULTS_DIR}/t6_build_host.log"

mkdir -p "${RESULTS_DIR}"

{
  echo "[T6 host build] start"

  g++ -O2 -std=c++20 \
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
    "${OSQP_DIR}/build/out/libosqp.a" \
    -lm -lrt -ldl \
    -o "${OUT_BIN}"

  file "${OUT_BIN}"
  echo "[T6 host build] PASS"
} > "${LOG_FILE}" 2>&1

echo "T6 host build PASS"
