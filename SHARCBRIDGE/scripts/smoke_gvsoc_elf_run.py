#!/usr/bin/env python3
"""Smoke test: run MPC ELF on GVSoC and assert firmware markers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_scripts_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))

from gvsoc_core import (  # noqa: E402
    GVSOC_BINARY,
    GVSOC_PLATFORM,
    GVSOC_RUN_TIMEOUT_S,
    GVSOC_TARGET,
    MPC_DIR,
    MPC_ELF,
    PULP_SDK_SOURCEME,
    VENV_ACTIVATE,
    validate_environment,
)


def main() -> int:
    if not validate_environment():
        print("FAIL: environment validation failed", file=sys.stderr)
        return 1

    cmd = (
        f"source {VENV_ACTIVATE} && "
        f"source {PULP_SDK_SOURCEME} && "
        f"timeout {GVSOC_RUN_TIMEOUT_S} {GVSOC_BINARY} "
        f"--target={GVSOC_TARGET} --platform={GVSOC_PLATFORM} "
        f"--binary={MPC_ELF} run"
    )

    result = subprocess.run(
        ["bash", "-c", cmd],
        cwd=str(MPC_DIR),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    if result.returncode != 0:
        print("FAIL: GVSoC returned non-zero exit code", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        return 2

    stdout = result.stdout
    missing = [token for token in ("MPC_START", "MPC_DONE") if token not in stdout]
    if missing:
        print(f"FAIL: missing firmware markers: {missing}", file=sys.stderr)
        return 3

    print("PASS: GVSoC ELF smoke run valid")
    print(f"binary={MPC_ELF}")
    print(f"target={GVSOC_TARGET} platform={GVSOC_PLATFORM}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
