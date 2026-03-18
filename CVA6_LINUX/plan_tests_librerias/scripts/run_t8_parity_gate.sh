#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="${ROOT_DIR}/results"

python3 "${ROOT_DIR}/scripts/compare_results.py" \
  "${RESULTS_DIR}" \
  "${RESULTS_DIR}/parity_report.json" \
  "${RESULTS_DIR}/parity_report.md"
