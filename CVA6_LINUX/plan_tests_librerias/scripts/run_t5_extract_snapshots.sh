#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAP_DIR="${ROOT_DIR}/snapshots"
RESULTS_DIR="${ROOT_DIR}/results"
INPUT_JSON="${INPUT_JSON:-/tmp/sharc_runs/2026-03-10--11-02-52-gvsoc_test/2026-03-10--03-02-54--gvsoc-test/gvsoc-serial/simulation_data_incremental.json}"
STATUS_MD="${RESULTS_DIR}/t5_snapshot_status.md"

mkdir -p "${SNAP_DIR}" "${RESULTS_DIR}"
rm -f "${SNAP_DIR}"/snapshot_*.json "${SNAP_DIR}/manifest.json"

python3 "${ROOT_DIR}/scripts/extract_sharc_snapshots.py" \
  --input "${INPUT_JSON}" \
  --output-dir "${SNAP_DIR}" \
  --indices "0,1,2,10,19" \
  > "${RESULTS_DIR}/t5_snapshot_extract.log"

python3 - "${SNAP_DIR}" > "${RESULTS_DIR}/t5_snapshot_validate.txt" <<'PYEOF'
import json
import sys
from pathlib import Path

snap_dir = Path(sys.argv[1])
files = sorted(snap_dir.glob("snapshot_*.json"))
if not files:
    raise SystemExit("NO_SNAPSHOTS")
for path in files:
    with path.open() as f:
        d = json.load(f)
    assert isinstance(d["x"], list) and len(d["x"]) == 3
    assert isinstance(d["w"], list) and len(d["w"]) == 2
    assert isinstance(d["u_prev"], list) and len(d["u_prev"]) == 2
    assert "k" in d and "t" in d
    print(f"{path.name}: k={d['k']} t={d['t']}")
print("SNAPSHOT_VALIDATE_PASS")
PYEOF

{
  echo "# Tarea 5. Snapshots"
  echo
  echo "## Estado"
  echo
  echo "\`PASS\`"
  echo
  echo "## Evidencia"
  echo
  echo "- source json: \`${INPUT_JSON}\`"
  echo "- snapshots dir: \`${SNAP_DIR}\`"
  echo "- manifest: \`${SNAP_DIR}/manifest.json\`"
  echo "- extract log: \`${RESULTS_DIR}/t5_snapshot_extract.log\`"
  echo "- validate: \`${RESULTS_DIR}/t5_snapshot_validate.txt\`"
  echo
  echo "## Resultado"
  echo
  echo "Se han congelado snapshots reales de una ejecucion previa de SHARC/GVSoC con campos \`k\`, \`t\`, \`x\`, \`w\`, \`u_prev\` y metadatos asociados."
} > "${STATUS_MD}"

echo "T5 snapshots PASS"
