#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"
PARITY_JSON="${RESULTS_DIR}/parity_report_fixed_interval.json"
OUT_MD="${RESULTS_DIR}/t9_integration_decision.md"

if [ ! -f "${PARITY_JSON}" ]; then
  echo "ERROR: missing ${PARITY_JSON}" >&2
  exit 2
fi

python3 - "${PARITY_JSON}" "${OUT_MD}" <<'PYEOF'
import json
import sys
from pathlib import Path

parity = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_md = Path(sys.argv[2])

ready = (
    parity.get("overall_status") == "PASS"
    and parity.get("formulation_status") == "PASS"
    and parity.get("iteration_match") is True
)

status = "PASS" if ready else "FAIL"
decision = "SI" if ready else "NO"

lines = [
    "# Tarea 9. Decision de integracion con SHARC",
    "",
    "## Estado",
    "",
    f"`{status}`",
    "",
    "## Decision",
    "",
    f"- integrar con SHARC: `{decision}`",
    "",
    "## Base tecnica",
    "",
    f"- overall parity: `{parity.get('overall_status')}`",
    f"- formulation parity: `{parity.get('formulation_status')}`",
    f"- iteration parity: `{parity.get('iteration_match')}`",
    f"- solver config: `adaptive_rho_interval={parity.get('solver_config', {}).get('adaptive_rho_interval_fixed')}`",
    "",
    "## Conclusion",
    "",
]

if ready:
    lines.extend([
        "- El camino CVA6 Linux ya es suficientemente fiel para abrir la integracion con SHARC.",
        "- La condicion tecnica es mantener la configuracion determinista de OSQP validada en T8.",
        "- El siguiente trabajo ya no es de compatibilidad de librerias, sino de integracion de arquitectura.",
    ])
else:
    lines.extend([
        "- No procede abrir la integracion con SHARC hasta cerrar T8.",
    ])

out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
PYEOF

