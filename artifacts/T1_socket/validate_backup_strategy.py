#!/usr/bin/env python3
"""Validate backup strategy document for T1_socket.6."""

from __future__ import annotations

import sys
from pathlib import Path


DOC = Path(__file__).with_name("backup_strategy.md")
REQUIRED = [
    "simplified_backup",
    "kernel_offload",
    "request_id",
    "fallback",
    "timeout",
]


def main() -> int:
    if not DOC.exists():
        print(f"ERROR: missing {DOC}")
        return 1
    text = DOC.read_text(encoding="utf-8")

    missing = [token for token in REQUIRED if token not in text]
    if missing:
        print("T1_socket.6 FAIL")
        for token in missing:
            print(f"- missing token: {token}")
        return 1

    print("T1_socket.6 PASS")
    print(f"- file: {DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

