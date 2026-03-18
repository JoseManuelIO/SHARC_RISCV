#!/usr/bin/env python3
"""Validate academic closure checklist for T8."""

from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "artifacts/T1_socket/results.md",
    "artifacts/T3_socket/overhead_ab_metrics.json",
    "artifacts/T4_socket/kernel_contract.md",
    "artifacts/T5_socket/kernel_bench_metrics.json",
    "artifacts/T6_socket/hotspots_report.json",
    "artifacts/T6_socket/incremental_ablation.json",
    "artifacts/T6_socket/equivalence_gate.json",
    "artifacts/T7_socket/load_campaign.json",
    "artifacts/T7_socket/soak_test.json",
    "artifacts/T7_socket/thesis_repro.json",
    "artifacts/plan_status_socket.md",
]


def _require_file(path: str, errors: list[str]) -> None:
    p = ROOT / path
    if not p.exists():
        errors.append(f"missing file: {path}")


def _require_json_pass(path: str, key: str, errors: list[str]) -> None:
    p = ROOT / path
    if not p.exists():
        errors.append(f"missing json: {path}")
        return
    try:
        data = json.loads(p.read_text())
    except Exception as exc:
        errors.append(f"invalid json {path}: {exc}")
        return
    if data.get(key) is not True:
        errors.append(f"{path} -> expected `{key}=true`")


def _require_status(path: str, expected_tokens: list[str], errors: list[str]) -> None:
    p = ROOT / path
    if not p.exists():
        errors.append(f"missing status file: {path}")
        return
    content = p.read_text()
    for tok in expected_tokens:
        if tok not in content:
            errors.append(f"{path} missing token: {tok}")


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        _require_file(rel, errors)

    _require_json_pass("artifacts/T3_socket/overhead_ab_metrics.json", "pass", errors)
    _require_json_pass("artifacts/T5_socket/kernel_bench_metrics.json", "global_pass", errors)
    _require_json_pass("artifacts/T6_socket/incremental_ablation.json", "pass", errors)
    _require_json_pass("artifacts/T6_socket/equivalence_gate.json", "pass", errors)
    _require_json_pass("artifacts/T7_socket/load_campaign.json", "pass", errors)
    _require_json_pass("artifacts/T7_socket/soak_test.json", "pass", errors)
    _require_json_pass("artifacts/T7_socket/thesis_repro.json", "pass", errors)

    _require_status(
        "artifacts/plan_status_socket.md",
        [
            "`T1_socket`: `PASS`",
            "`T2_socket`: `PASS`",
            "`T3_socket`: `PASS`",
            "`T4_socket`: `PASS`",
            "`T5_socket`: `PASS`",
            "`T6_socket`: `PASS`",
            "`T7_socket`: `PASS`",
            "`T8_socket`: `PASS`",
        ],
        errors,
    )

    if errors:
        print("T8_socket.2 FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("T8_socket.2 PASS")
    print("- checklist complete and traceable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
