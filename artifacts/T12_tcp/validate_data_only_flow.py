#!/usr/bin/env python3
"""Validate that persistent flow avoids per-iteration relaunch/patch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _last_int(pattern: str, text: str) -> int | None:
    hits = re.findall(pattern, text)
    if not hits:
        return None
    return int(hits[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=Path("/tmp/tcp_figure5.log"))
    parser.add_argument("--expect-spawn", type=int, default=1)
    parser.add_argument("--expect-patch", type=int, default=1)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/T12_tcp/data_only_flow_latest.json"),
    )
    args = parser.parse_args()

    if not args.log.exists():
        print(f"ERROR: log not found: {args.log}")
        return 1

    text = args.log.read_text(encoding="utf-8", errors="replace")
    spawn_count = _last_int(r"spawn_count=(\d+)", text)
    patch_count = _last_int(r"elf_patch_count=(\d+)", text)

    pass_spawn = spawn_count == args.expect_spawn
    pass_patch = patch_count == args.expect_patch
    ok = pass_spawn and pass_patch

    report = {
        "log": str(args.log),
        "spawn_count": spawn_count,
        "elf_patch_count": patch_count,
        "expect_spawn": args.expect_spawn,
        "expect_patch": args.expect_patch,
        "pass_spawn": pass_spawn,
        "pass_patch": pass_patch,
        "pass": ok,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(json.dumps(report, indent=2))
    if not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
