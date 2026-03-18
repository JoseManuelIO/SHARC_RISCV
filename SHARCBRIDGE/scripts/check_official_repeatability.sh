#!/usr/bin/env bash
# Run official short config twice and compare key end-state metrics.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

if [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi

run_once() {
  local tag="$1"
  SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_config.sh gvsoc_test.json >/tmp/repeat_${tag}.log 2>&1
  local out
  out=$(rg -n "^Output directory:" /tmp/repeat_${tag}.log | tail -n1 | sed -E 's/^[0-9]+:Output directory: //')
  if [ -z "$out" ]; then
    echo "ERROR: could not detect output directory for run ${tag}" >&2
    cat /tmp/repeat_${tag}.log >&2
    exit 1
  fi
  echo "$out"
}

r1=$(run_once A)
r2=$(run_once B)

python3 - "$r1" "$r2" <<'PY'
import glob, json, os, sys

def get_sim(run_dir):
    files = sorted(glob.glob(os.path.join(run_dir, '**', 'simulation_data_incremental.json'), recursive=True))
    if not files:
        raise SystemExit(f'ERROR: no simulation_data_incremental.json in {run_dir}')
    return json.load(open(files[0], 'r', encoding='utf-8'))

a = get_sim(sys.argv[1])
b = get_sim(sys.argv[2])

xa = a['x'][-1]
xb = b['x'][-1]
ua = a['u'][-1]
ub = b['u'][-1]

def max_abs_diff(v1, v2):
    return max(abs(float(x)-float(y)) for x,y in zip(v1,v2))

dx = max_abs_diff(xa, xb)
du = max_abs_diff(ua, ub)

# Tight tolerance for deterministic flow on same machine.
tol = 1e-6
ok = dx <= tol and du <= tol

report = {
    'run_a': sys.argv[1],
    'run_b': sys.argv[2],
    'x_last_a': xa,
    'x_last_b': xb,
    'u_last_a': ua,
    'u_last_b': ub,
    'dx_max_abs': dx,
    'du_max_abs': du,
    'tol': tol,
    'pass': ok,
}
print(json.dumps(report, indent=2))
raise SystemExit(0 if ok else 1)
PY

echo "PASS: repeatability check"
