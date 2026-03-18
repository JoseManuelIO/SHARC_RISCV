#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAP_DIR="${ROOT_DIR}/snapshots"
RESULTS_DIR="${ROOT_DIR}/results"
CONFIG_JSON="${CONFIG_JSON:-${ROOT_DIR}/../../sharc_original/examples/acc_example/base_config.json}"
STATUS_MD="${RESULTS_DIR}/t6_host_status.md"

mkdir -p "${RESULTS_DIR}"

bash "${ROOT_DIR}/scripts/build_acc_snapshot_host.sh"

for snap in "${SNAP_DIR}"/snapshot_*.json; do
  base="$(basename "${snap}" .json)"
  raw_out="${RESULTS_DIR}/host_${base}.raw.txt"
  json_out="${RESULTS_DIR}/host_${base}.json"
  "${RESULTS_DIR}/acc_snapshot_host" "${CONFIG_JSON}" "${snap}" > "${raw_out}"
  python3 - "${raw_out}" "${json_out}" <<'PYEOF'
import sys

raw_path, json_path = sys.argv[1], sys.argv[2]
with open(raw_path, "r", encoding="utf-8") as f:
    text = f.read()
start = text.find("{")
if start < 0:
    raise SystemExit("JSON_START_NOT_FOUND")
payload = text[start:].strip()
with open(json_path, "w", encoding="utf-8") as f:
    f.write(payload)
PYEOF
done

python3 - "${RESULTS_DIR}" > "${RESULTS_DIR}/t6_host_validate.txt" <<'PYEOF'
import json
import sys
from pathlib import Path

results = Path(sys.argv[1])
files = sorted(results.glob("host_snapshot_*.json"))
if not files:
    raise SystemExit("NO_HOST_RESULTS")
for path in files:
    with path.open() as f:
        d = json.load(f)
    assert "u" in d and len(d["u"]) == 2
    assert "metadata" in d
    print(f"{path.name}: k={d['k']} u={d['u']}")
print("T6_HOST_VALIDATE_PASS")
PYEOF

{
  echo "# Tarea 6. Host Standalone"
  echo
  echo "## Estado"
  echo
  echo "\`PASS\`"
  echo
  echo "## Evidencia"
  echo
  echo "- build log: \`${RESULTS_DIR}/t6_build_host.log\`"
  echo "- validation: \`${RESULTS_DIR}/t6_host_validate.txt\`"
  echo "- outputs: \`${RESULTS_DIR}/host_snapshot_*.json\`"
  echo
  echo "## Resultado"
  echo
  echo "El controlador ACC original se ejecuta en host de forma standalone usando snapshots reales congelados."
} > "${STATUS_MD}"

echo "T6 host snapshots PASS"
