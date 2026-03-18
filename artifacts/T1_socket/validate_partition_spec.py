#!/usr/bin/env python3
"""Validate T1 partition specification completeness/consistency."""

from __future__ import annotations

import re
import sys
from pathlib import Path


DOC = Path(__file__).with_name("partition_sharc_pulp.md")

REQUIRED_SNIPPETS = [
    "Construcción de `P,q,A,l,u`",
    "`y = P*x`",
    "`y = A*x`",
    "`y = A^T*x`",
    "`dot(x,y)`",
    "`axpy/scal`",
    "Proyección en caja",
]


def main() -> int:
    if not DOC.exists():
        print(f"ERROR: missing {DOC}")
        return 1

    text = DOC.read_text(encoding="utf-8")
    errors: list[str] = []

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"missing required operation snippet: {snippet}")

    # Ensure there is at least one HOST row and one PULP row in the markdown table.
    host_rows = len(re.findall(r"\|\s*HOST\s*\|", text))
    pulp_rows = len(re.findall(r"\|\s*PULP\s*\|", text))
    if host_rows == 0:
        errors.append("no HOST rows found in partition table")
    if pulp_rows == 0:
        errors.append("no PULP rows found in partition table")

    if errors:
        print("T1_socket.5 FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("T1_socket.5 PASS")
    print(f"- file: {DOC}")
    print(f"- host_rows: {host_rows}")
    print(f"- pulp_rows: {pulp_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

