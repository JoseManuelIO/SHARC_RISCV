#!/bin/bash
# run_gvsoc_figure5_tcp_persistent.sh
#
# Figure 5 over TCP forcing persistent mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

GVSOC_EXEC_MODE="${GVSOC_EXEC_MODE:-persistent}"
GVSOC_PERSISTENT_WORKERS="${GVSOC_PERSISTENT_WORKERS:-1}"
GVSOC_PORT="${GVSOC_PORT:-5003}"
GVSOC_PERSISTENT_PATH="${GVSOC_PERSISTENT_PATH:-gvsoc_legacy}"
SHARC_OFFICIAL_RISCV_MODE="${SHARC_OFFICIAL_RISCV_MODE:-1}"
SHARC_DOUBLE_NATIVE="${SHARC_DOUBLE_NATIVE:-0}"

if [ "$GVSOC_EXEC_MODE" != "persistent" ]; then
    echo "ERROR: run_gvsoc_figure5_tcp_persistent.sh requires GVSOC_EXEC_MODE=persistent"
    exit 1
fi

GVSOC_EXEC_MODE="$GVSOC_EXEC_MODE" \
GVSOC_PERSISTENT_WORKERS="$GVSOC_PERSISTENT_WORKERS" \
GVSOC_PORT="$GVSOC_PORT" \
GVSOC_PERSISTENT_PATH="$GVSOC_PERSISTENT_PATH" \
SHARC_OFFICIAL_RISCV_MODE="$SHARC_OFFICIAL_RISCV_MODE" \
SHARC_DOUBLE_NATIVE="$SHARC_DOUBLE_NATIVE" \
    bash "$SCRIPT_DIR/run_gvsoc_figure5_tcp.sh"

if [ "${GVSOC_QP_SOLVE:-0}" = "1" ]; then
    python3 - <<'PYEOF'
from pathlib import Path
import json
import re
import sys

log = Path('/tmp/tcp_figure5.log')
if not log.exists():
    print('ERROR: /tmp/tcp_figure5.log not found')
    sys.exit(1)
text = log.read_text(encoding='utf-8', errors='replace')
hits = re.findall(r"\[Server\] qp_solve n=(\d+) m=(\d+) status=(\w+)", text)
ok = len(hits) > 0
report = {
    'log': str(log),
    'qp_solve_calls': len(hits),
    'pass': ok,
}
print(json.dumps(report, indent=2))
sys.exit(0 if ok else 1)
PYEOF
else
    python3 "$REPO_DIR/artifacts/T12_tcp/validate_data_only_flow.py" \
        --log /tmp/tcp_figure5.log \
        --expect-spawn 1 \
        --expect-patch 1
fi
