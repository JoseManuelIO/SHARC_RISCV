#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
KNOWN_GOOD_SDK_DIR="${CVA6_KNOWN_GOOD_SDK_DIR:-/tmp/cva6-sdk-clean-20260324-r1-2}"
REPO_SDK_DIR="${REPO_DIR}/CVA6_LINUX/cva6-sdk"
if [ -n "${CVA6_SDK_DIR:-}" ]; then
  SDK_DIR="${CVA6_SDK_DIR}"
elif [ -d "${KNOWN_GOOD_SDK_DIR}" ]; then
  SDK_DIR="${KNOWN_GOOD_SDK_DIR}"
else
  SDK_DIR="${REPO_SDK_DIR}"
fi
BUILD_DIR="${ROOT_DIR}/build"
PATCHED_OSQP_SRC="${BUILD_DIR}/osqp-fixed-interval-src"
PATCH_INTERVAL="${CVA6_OSQP_ADAPTIVE_RHO_INTERVAL:-25}"

LIBMPC_DIR="${REPO_DIR}/sharc_original/libmpc"
CTRL_INCLUDE_DIR="${REPO_DIR}/sharc_original/resources/controllers/include"
CTRL_SRC_DIR="${REPO_DIR}/sharc_original/resources/controllers/src"
RES_INCLUDE_DIR="${REPO_DIR}/sharc_original/resources/include"
EIGEN_DIR="${REPO_DIR}/CVA6_LINUX/deps/eigen"
OSQP_SRC_DIR="${REPO_DIR}/CVA6_LINUX/deps/osqp"

TARGET_BIN_DIR="${SDK_DIR}/buildroot/output/target/usr/bin"
TARGET_SHARE_DIR="${SDK_DIR}/buildroot/output/target/usr/share/sharcbridge_cva6"
TARGET_CONFIG="${TARGET_SHARE_DIR}/base_config.json"
OUT_BIN="${BUILD_DIR}/cva6_acc_runtime"
OSQP_BUILD_DIR="${BUILD_DIR}/osqp-cva6-fixed-interval"
SHIM_DIR="${BUILD_DIR}/include_shims"

mkdir -p "${BUILD_DIR}" "${TARGET_BIN_DIR}" "${TARGET_SHARE_DIR}" "${SHIM_DIR}/osqp"

if [ ! -d "${PATCHED_OSQP_SRC}" ]; then
  cp -a "${OSQP_SRC_DIR}" "${PATCHED_OSQP_SRC}"
fi

python3 - "${PATCHED_OSQP_SRC}/include/constants.h" "${PATCH_INTERVAL}" <<'PYEOF'
import sys
from pathlib import Path

path = Path(sys.argv[1])
interval = sys.argv[2]
text = path.read_text(encoding="utf-8")
old = "#  define ADAPTIVE_RHO_INTERVAL (0)"
new = f"#  define ADAPTIVE_RHO_INTERVAL ({interval})"
if old in text:
    text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
PYEOF

cat > "${SHIM_DIR}/osqp/osqp.h" <<EOF
#include "${PATCHED_OSQP_SRC}/include/osqp.h"
EOF

export PATH="${SDK_DIR}/buildroot/output/host/bin:${PATH}"
export CCACHE_DIR=/tmp/buildroot-ccache
mkdir -p "${CCACHE_DIR}"

cmake -S "${PATCHED_OSQP_SRC}" -B "${OSQP_BUILD_DIR}" \
  -DUNITTESTS=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DPRINTING=ON \
  -DPROFILING=ON \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_C_COMPILER=riscv64-linux-gcc
cmake --build "${OSQP_BUILD_DIR}" -j"$(nproc)"

riscv64-linux-g++ -O2 -std=c++20 \
  -DTNX=3 -DTNU=2 -DTNDU=2 -DTNY=1 \
  -DPREDICTION_HORIZON=5 -DCONTROL_HORIZON=5 \
  -I"${CTRL_INCLUDE_DIR}" \
  -I"${RES_INCLUDE_DIR}" \
  -I"${LIBMPC_DIR}/include" \
  -I"${EIGEN_DIR}" \
  -I"${SHIM_DIR}" \
  "${ROOT_DIR}/cva6_acc_runtime.cpp" \
  "${CTRL_SRC_DIR}/controller.cpp" \
  "${CTRL_SRC_DIR}/ACC_Controller.cpp" \
  "${OSQP_BUILD_DIR}/out/libosqp.a" \
  -lm -lrt -ldl \
  -o "${OUT_BIN}"

cp "${OUT_BIN}" "${TARGET_BIN_DIR}/sharc_cva6_acc_runtime"
cp "${REPO_DIR}/sharc_original/examples/acc_example/base_config.json" "${TARGET_CONFIG}"

make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)"
cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${SDK_DIR}/install64/vmlinux"
(cd "${SDK_DIR}" && make spike_payload)

echo "CVA6 image build PASS"
echo "binary=${OUT_BIN}"
echo "target_binary=${TARGET_BIN_DIR}/sharc_cva6_acc_runtime"
echo "target_config=${TARGET_CONFIG}"
