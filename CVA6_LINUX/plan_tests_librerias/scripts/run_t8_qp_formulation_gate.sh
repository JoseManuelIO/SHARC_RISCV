#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
SNAP_DIR="${ROOT_DIR}/snapshots"
HOST_BIN="${RESULTS_DIR}/acc_snapshot_host"
HOST_CFG="${ROOT_DIR}/../../sharc_original/examples/acc_example/base_config.json"
SPIKE_LOG="${RESULTS_DIR}/t8_qp_formulation_spike.log"
TARGET_BIN_DIR="${SDK_DIR}/buildroot/output/target/usr/bin"
TARGET_SHARE_DIR="${SDK_DIR}/buildroot/output/target/usr/share/plan_tests_librerias"
TARGET_SNAP_DIR="${TARGET_SHARE_DIR}/snapshots"

mkdir -p "${RESULTS_DIR}"

if [ ! -x "${HOST_BIN}" ]; then
  echo "ERROR: missing host binary ${HOST_BIN}" >&2
  exit 2
fi

for snapshot in "${SNAP_DIR}"/snapshot_*.json; do
  base="$(basename "${snapshot}" .json)"
  export SHARC_QP_EXPORT_PATH="${RESULTS_DIR}/host_qp_${base}.jsonl"
  export SHARC_QP_EXPORT_MAX_SAMPLES=1
  rm -f "${SHARC_QP_EXPORT_PATH}"
  "${HOST_BIN}" "${HOST_CFG}" "${snapshot}" > /dev/null
  python3 - "${SHARC_QP_EXPORT_PATH}" "${RESULTS_DIR}/host_qp_${base}.json" <<'PYEOF'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = [line.strip() for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
if len(lines) != 1:
    raise SystemExit(f"EXPECTED_ONE_QP_SAMPLE:{src}")
dst.write_text(json.dumps(json.loads(lines[0]), indent=2), encoding="utf-8")
PYEOF
done
unset SHARC_QP_EXPORT_PATH SHARC_QP_EXPORT_MAX_SAMPLES

cat > "${TARGET_BIN_DIR}/plan_acc_qp_batch.sh" <<'SHEOF'
#!/bin/sh
set -e
CFG=/usr/share/plan_tests_librerias/base_config.json
BIN=/usr/bin/plan_acc_snapshot_cva6
for s in /usr/share/plan_tests_librerias/snapshots/snapshot_*.json; do
  base=$(basename "$s" .json)
  export SHARC_QP_EXPORT_PATH=/tmp/${base}.jsonl
  export SHARC_QP_EXPORT_MAX_SAMPLES=1
  rm -f "${SHARC_QP_EXPORT_PATH}"
  "$BIN" "$CFG" "$s" >/dev/null
  echo "QP_BEGIN:${base}"
  cat "${SHARC_QP_EXPORT_PATH}"
  echo "QP_END:${base}"
done
echo "T8_QP_BATCH_DONE"
SHEOF
chmod +x "${TARGET_BIN_DIR}/plan_acc_qp_batch.sh"

mkdir -p "${TARGET_SNAP_DIR}"
cp "${SNAP_DIR}"/snapshot_*.json "${TARGET_SNAP_DIR}/"
cp "${ROOT_DIR}/../../sharc_original/examples/acc_example/base_config.json" "${TARGET_SHARE_DIR}/base_config.json"

export CCACHE_DIR=/tmp/buildroot-ccache
mkdir -p "${CCACHE_DIR}"
make -C "${SDK_DIR}/buildroot" linux-rebuild-with-initramfs -j"$(nproc)" > "${RESULTS_DIR}/t8_qp_build.log" 2>&1
cp "${SDK_DIR}/buildroot/output/images/vmlinux" "${SDK_DIR}/install64/vmlinux"
(cd "${SDK_DIR}" && make spike_payload >> "${RESULTS_DIR}/t8_qp_build.log" 2>&1)

python3 "${ROOT_DIR}/scripts/run_spike_noninteractive.py" \
  --spike "${SDK_DIR}/install64/bin/spike" \
  --payload "${SDK_DIR}/install64/spike_fw_payload.elf" \
  --command "plan_acc_qp_batch.sh" \
  --expect "T8_QP_BATCH_DONE" \
  --log "${SPIKE_LOG}" \
  --boot-timeout 60 \
  --shutdown-timeout 20

python3 - "${SPIKE_LOG}" "${RESULTS_DIR}" <<'PYEOF'
import json
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
results_dir = Path(sys.argv[2])
lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

current = None
buffer = []
for line in lines:
    if line.startswith("QP_BEGIN:"):
        current = line.split(":", 1)[1].strip()
        buffer = []
        continue
    if line.startswith("QP_END:"):
        if current is None:
            continue
        text = "\n".join(buffer).strip()
        if not text:
            raise SystemExit(f"EMPTY_QP_EXPORT:{current}")
        payload = json.loads(text.splitlines()[-1])
        out = results_dir / f"cva6_qp_{current}.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        current = None
        buffer = []
        continue
    if current is not None:
        buffer.append(line)
PYEOF

python3 - "${RESULTS_DIR}" > "${RESULTS_DIR}/t8_qp_formulation_compare.txt" <<'PYEOF'
import json
import math
import sys
from pathlib import Path

results = Path(sys.argv[1])
tol = 1e-9
failed = []

def compare_list(name, a, b, tol):
    if len(a) != len(b):
        failed.append(f"{name}:len:{len(a)}:{len(b)}")
        return 0.0
    max_diff = 0.0
    for i, (av, bv) in enumerate(zip(a, b)):
        if av is None and bv is None:
            continue
        if av is None or bv is None:
            failed.append(f"{name}[{i}]:null-mismatch")
            continue
        diff = abs(av - bv)
        max_diff = max(max_diff, diff)
        if diff > tol:
            failed.append(f"{name}[{i}]={diff}")
    return max_diff

for host_path in sorted(results.glob("host_qp_snapshot_*.json")):
    suffix = host_path.name.replace("host_qp_", "")
    cva6_path = results / f"cva6_qp_{suffix}"
    if not cva6_path.exists():
        failed.append(f"missing:{cva6_path.name}")
        continue

    host = json.loads(host_path.read_text())
    cva6 = json.loads(cva6_path.read_text())

    for key in ("n", "m", "p_nnz", "a_nnz"):
        if host[key] != cva6[key]:
            failed.append(f"{suffix}:{key}:{host[key]}:{cva6[key]}")

    for key in ("P_colptr", "P_rowind", "A_colptr", "A_rowind"):
        max_diff = compare_list(f"{suffix}:{key}", host[key], cva6[key], 0.0)
        print(f"{suffix}:{key}:max_diff={max_diff:.3e}")

    for key in ("P_data", "q", "A_data", "l", "u"):
        max_diff = compare_list(f"{suffix}:{key}", host[key], cva6[key], tol)
        print(f"{suffix}:{key}:max_diff={max_diff:.3e}")

if failed:
    print("T8_QP_FORMULATION_FAIL")
    for item in failed:
        print(item)
    raise SystemExit(4)

print("T8_QP_FORMULATION_PASS")
PYEOF
