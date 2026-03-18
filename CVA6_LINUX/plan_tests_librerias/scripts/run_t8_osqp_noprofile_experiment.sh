#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
BUILD_DIR="${ROOT_DIR}/build"
SNAP_DIR="${ROOT_DIR}/snapshots"
LIBMPC_DIR="${ROOT_DIR}/../../sharc_original/libmpc"
CTRL_INCLUDE_DIR="${ROOT_DIR}/../../sharc_original/resources/controllers/include"
CTRL_SRC_DIR="${ROOT_DIR}/../../sharc_original/resources/controllers/src"
RES_INCLUDE_DIR="${ROOT_DIR}/../../sharc_original/resources/include"
EIGEN_DIR="${ROOT_DIR}/../deps/eigen"
OSQP_DIR="${ROOT_DIR}/../deps/osqp"
HOST_CFG="${ROOT_DIR}/../../sharc_original/examples/acc_example/base_config.json"
HOST_OSQP_BUILD="${BUILD_DIR}/osqp-host-noprofile"
CVA6_OSQP_BUILD="${BUILD_DIR}/osqp-cva6-noprofile"
HOST_BIN="${BUILD_DIR}/acc_snapshot_host_noprofile"
CVA6_BIN="${BUILD_DIR}/acc_snapshot_cva6_noprofile"
SPIKE_LOG="${RESULTS_DIR}/t8_osqp_noprofile_spike.log"
REPORT_TXT="${RESULTS_DIR}/t8_osqp_noprofile_compare.txt"
REPORT_MD="${RESULTS_DIR}/t8_osqp_noprofile_report.md"

mkdir -p "${RESULTS_DIR}" "${BUILD_DIR}"

cmake -S "${OSQP_DIR}" -B "${HOST_OSQP_BUILD}" \
  -DUNITTESTS=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DPROFILING=OFF \
  -DPRINTING=ON
cmake --build "${HOST_OSQP_BUILD}" -j"$(nproc)"

export PATH="${SDK_DIR}/buildroot/output/host/bin:${PATH}"
export CCACHE_DIR=/tmp/buildroot-ccache
mkdir -p "${CCACHE_DIR}"

cmake -S "${OSQP_DIR}" -B "${CVA6_OSQP_BUILD}" \
  -DUNITTESTS=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DPROFILING=OFF \
  -DPRINTING=ON \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_C_COMPILER=riscv64-linux-gcc
cmake --build "${CVA6_OSQP_BUILD}" -j"$(nproc)"

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
  "${HOST_OSQP_BUILD}/out/libosqp.a" \
  -lm -lrt -ldl \
  -o "${HOST_BIN}"

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
  "${CVA6_OSQP_BUILD}/out/libosqp.a" \
  -lm -lrt -ldl \
  -o "${CVA6_BIN}"

for snapshot in "${SNAP_DIR}"/snapshot_*.json; do
  base="$(basename "${snapshot}" .json)"
  raw="${RESULTS_DIR}/host_noprofile_${base}.raw.txt"
  out="${RESULTS_DIR}/host_noprofile_${base}.json"
  "${HOST_BIN}" "${HOST_CFG}" "${snapshot}" > "${raw}"
  python3 - "${raw}" "${out}" <<'PYEOF'
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
start = raw.find("{")
if start < 0:
    raise SystemExit(f"JSON_START_NOT_FOUND:{sys.argv[1]}")
Path(sys.argv[2]).write_text(raw[start:].strip() + "\n", encoding="utf-8")
PYEOF
done

TARGET_BIN_DIR="${SDK_DIR}/buildroot/output/target/usr/bin"
TARGET_SHARE_DIR="${SDK_DIR}/buildroot/output/target/usr/share/plan_tests_librerias"
TARGET_SNAP_DIR="${TARGET_SHARE_DIR}/snapshots"
mkdir -p "${TARGET_BIN_DIR}" "${TARGET_SNAP_DIR}"
cp "${CVA6_BIN}" "${TARGET_BIN_DIR}/plan_acc_snapshot_cva6_noprofile"
cp "${HOST_CFG}" "${TARGET_SHARE_DIR}/base_config.json"
cp "${SNAP_DIR}"/snapshot_*.json "${TARGET_SNAP_DIR}/"

cat > "${TARGET_BIN_DIR}/plan_acc_snapshot_batch_noprofile.sh" <<'SHEOF'
#!/bin/sh
set -e
CFG=/usr/share/plan_tests_librerias/base_config.json
BIN=/usr/bin/plan_acc_snapshot_cva6_noprofile
for s in /usr/share/plan_tests_librerias/snapshots/snapshot_*.json; do
  base=$(basename "$s" .json)
  echo "SNAP_BEGIN:${base}"
  "$BIN" "$CFG" "$s"
  echo "SNAP_END:${base}"
done
echo "T8_OSQP_NOPROFILE_DONE"
SHEOF
chmod +x "${TARGET_BIN_DIR}/plan_acc_snapshot_batch_noprofile.sh"

make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)" > "${RESULTS_DIR}/t8_osqp_noprofile_build.log" 2>&1
cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${SDK_DIR}/install64/vmlinux"
(cd "${SDK_DIR}" && make spike_payload >> "${RESULTS_DIR}/t8_osqp_noprofile_build.log" 2>&1)

python3 "${ROOT_DIR}/scripts/run_spike_noninteractive.py" \
  --spike "${SDK_DIR}/install64/bin/spike" \
  --payload "${SDK_DIR}/install64/spike_fw_payload.elf" \
  --command "plan_acc_snapshot_batch_noprofile.sh" \
  --expect "T8_OSQP_NOPROFILE_DONE" \
  --log "${SPIKE_LOG}" \
  --boot-timeout 60 \
  --shutdown-timeout 20

python3 - "${SPIKE_LOG}" "${RESULTS_DIR}" <<'PYEOF'
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
results_dir = Path(sys.argv[2])
lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

current = None
buffer = []
for line in lines:
    if line.startswith("SNAP_BEGIN:"):
        current = line.split(":", 1)[1].strip()
        buffer = []
        continue
    if line.startswith("SNAP_END:"):
        if current is None:
            continue
        text = "\n".join(buffer)
        start = text.find("{")
        if start < 0:
            raise SystemExit(f"JSON_START_NOT_FOUND:{current}")
        payload = text[start:].strip()
        out = results_dir / f"cva6_noprofile_{current}.json"
        out.write_text(payload + "\n", encoding="utf-8")
        current = None
        buffer = []
        continue
    if current is not None:
        buffer.append(line)
PYEOF

python3 - "${RESULTS_DIR}" > "${REPORT_TXT}" <<'PYEOF'
import json
import sys
from pathlib import Path

results = Path(sys.argv[1])
failed = []

max_u0 = 0.0
max_u1 = 0.0
max_cost = 0.0
max_iter = 0.0

for host_path in sorted(results.glob("host_noprofile_snapshot_*.json")):
    suffix = host_path.name.replace("host_noprofile_", "")
    cva6_path = results / f"cva6_noprofile_{suffix}"
    if not cva6_path.exists():
        failed.append(f"missing:{cva6_path.name}")
        continue
    host = json.loads(host_path.read_text())
    cva6 = json.loads(cva6_path.read_text())
    u0 = abs(host["u"][0] - cva6["u"][0])
    u1 = abs(host["u"][1] - cva6["u"][1])
    cost = abs(host["metadata"]["cost"] - cva6["metadata"]["cost"])
    it = abs(host["metadata"]["iterations"] - cva6["metadata"]["iterations"])
    max_u0 = max(max_u0, u0)
    max_u1 = max(max_u1, u1)
    max_cost = max(max_cost, cost)
    max_iter = max(max_iter, it)
    print(f"{suffix}:u0={u0:.6e} u1={u1:.6e} cost={cost:.6e} iter={it:.6e}")
    if it != 0:
        failed.append(f"{suffix}:iter:{it}")

print(f"MAX_u0={max_u0:.6e}")
print(f"MAX_u1={max_u1:.6e}")
print(f"MAX_cost={max_cost:.6e}")
print(f"MAX_iter={max_iter:.6e}")
if failed:
    print("T8_OSQP_NOPROFILE_FAIL")
    raise SystemExit(4)
print("T8_OSQP_NOPROFILE_PASS")
PYEOF

{
  echo "# Experimento OSQP sin profiling"
  echo
  echo "- build log: \`${RESULTS_DIR}/t8_osqp_noprofile_build.log\`"
  echo "- spike log: \`${SPIKE_LOG}\`"
  echo "- compare: \`${REPORT_TXT}\`"
} > "${REPORT_MD}"
