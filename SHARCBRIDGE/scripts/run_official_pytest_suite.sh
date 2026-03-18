#!/bin/bash
# Official SHARCBRIDGE pytest suite (TCP + double pipeline)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

if [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi

pytest -q SHARCBRIDGE/tests
