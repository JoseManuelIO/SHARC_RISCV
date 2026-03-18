#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/../cva6-sdk"
RESULTS_DIR="${ROOT_DIR}/results"
STATUS_MD="${RESULTS_DIR}/t7_cva6_status.md"
SPIKE_LOG="${RESULTS_DIR}/t7_cva6_snapshots.log"

mkdir -p "${RESULTS_DIR}"

bash "${ROOT_DIR}/scripts/build_acc_snapshot_cva6.sh"

python3 "${ROOT_DIR}/scripts/run_spike_noninteractive.py" \
  --spike "${SDK_DIR}/install64/bin/spike" \
  --payload "${SDK_DIR}/install64/spike_fw_payload.elf" \
  --command "plan_acc_snapshot_batch.sh" \
  --expect "T7_BATCH_DONE" \
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
        out = results_dir / f"cva6_{current}.json"
        out.write_text(payload, encoding="utf-8")
        current = None
        buffer = []
        continue
    if current is not None:
        buffer.append(line)
PYEOF

python3 - "${RESULTS_DIR}" > "${RESULTS_DIR}/t7_cva6_validate.txt" <<'PYEOF'
import json
import sys
from pathlib import Path

results = Path(sys.argv[1])
host_files = sorted(results.glob("host_snapshot_*.json"))
if not host_files:
    raise SystemExit("NO_HOST_FILES")

missing = []
for host_path in host_files:
    suffix = host_path.name.replace("host_", "")
    cva6_path = results / f"cva6_{suffix}"
    if not cva6_path.exists():
        missing.append(cva6_path.name)
        continue
    payload = json.loads(cva6_path.read_text())
    if "u" not in payload or "metadata" not in payload:
        raise SystemExit(f"INVALID_PAYLOAD:{cva6_path.name}")
    print(f"{cva6_path.name}: solver_status={payload['metadata'].get('solver_status')} iterations={payload['metadata'].get('iterations')}")

if missing:
    print("T7_VALIDATE_FAIL")
    raise SystemExit("MISSING_OUTPUTS:" + ",".join(missing))

print("T7_VALIDATE_PASS")
PYEOF

{
  echo "# Tarea 7. CVA6 Standalone"
  echo
  echo "## Estado"
  echo
  echo "\`PASS\`"
  echo
  echo "## Evidencia"
  echo
  echo "- build log: \`${RESULTS_DIR}/t7_build_cva6.log\`"
  echo "- spike log: \`${SPIKE_LOG}\`"
  echo "- validate: \`${RESULTS_DIR}/t7_cva6_validate.txt\`"
  echo "- outputs: \`${RESULTS_DIR}/cva6_snapshot_*.json\`"
  echo
  echo "## Resultado"
  echo
  echo "El controlador ACC original se ejecuta en CVA6 Linux sobre los snapshots congelados y genera salidas JSON validas."
} > "${STATUS_MD}"

echo "T7 cva6 snapshots PASS"
