#!/usr/bin/env python3
"""
T3 gate: host QP formulation parity + official path contract checks.

Checks:
1) Numeric parity between host original formulation (c_abi direct) and
   exported payload after framing round-trip (encode/decode).
2) TCP log evidence contains per-iteration payload trace with fields=P,q,A,l,u.
3) Official static contract: wrapper sends x/w/u_prev (not qp_payload), server enforces c_abi no-fallback.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "SHARCBRIDGE" / "scripts"
WRAPPER_PATH = REPO_ROOT / "SHARCBRIDGE" / "sharc_patches" / "acc_example" / "gvsoc_controller_wrapper_v2.py"
SERVER_PATH = REPO_ROOT / "SHARCBRIDGE" / "scripts" / "gvsoc_tcp_server.py"

DEFAULT_JSON = REPO_ROOT / "artifacts" / "T3_formulation_parity_gate_latest.json"
DEFAULT_MD = REPO_ROOT / "artifacts" / "T3_formulation_parity_gate_latest.md"
DEFAULT_TCP_LOG = Path("/tmp/tcp_generic.log")

NUM_FIELDS = ("P_data", "q", "A_data", "l", "u")
INT_FIELDS = ("P_colptr", "P_rowind", "A_colptr", "A_rowind")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compare_payloads(payload_a: dict[str, Any], payload_b: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "int_equal": True,
        "int_mismatches": [],
        "max_abs_by_field": {},
        "max_abs_overall": 0.0,
    }

    for key in INT_FIELDS:
        va = payload_a.get(key)
        vb = payload_b.get(key)
        if va != vb:
            out["int_equal"] = False
            out["int_mismatches"].append({"field": key, "a": va, "b": vb})

    for key in NUM_FIELDS:
        arr_a = payload_a.get(key, [])
        arr_b = payload_b.get(key, [])
        if len(arr_a) != len(arr_b):
            out["int_equal"] = False
            out["int_mismatches"].append(
                {"field": key, "a_len": len(arr_a), "b_len": len(arr_b)}
            )
            out["max_abs_by_field"][key] = float("inf")
            out["max_abs_overall"] = float("inf")
            continue
        max_abs = 0.0
        for a, b in zip(arr_a, arr_b):
            d = abs(float(a) - float(b))
            if d > max_abs:
                max_abs = d
            if d > out["max_abs_overall"]:
                out["max_abs_overall"] = d
        out["max_abs_by_field"][key] = max_abs

    return out


def _iter_trace_records(trace_path: Path):
    with trace_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            x = rec.get("x")
            w = rec.get("w")
            u_prev = rec.get("u_prev")
            if (
                isinstance(x, list)
                and len(x) == 3
                and isinstance(w, list)
                and len(w) == 2
                and isinstance(u_prev, list)
                and len(u_prev) == 2
            ):
                yield {
                    "x": [float(x[0]), float(x[1]), float(x[2])],
                    "w": [float(w[0]), float(w[1])],
                    "u_prev": [float(u_prev[0]), float(u_prev[1])],
                    "source": str(trace_path),
                }


def build_corpus(max_samples: int) -> list[dict[str, Any]]:
    trace_candidates: list[Path] = []
    trace_candidates += sorted(Path("/tmp/sharc_runs").glob("*-ab_onestep_compare/**/wrapper_dynamics_trace.ndjson"))
    trace_candidates += sorted(Path("/tmp/sharc_runs").glob("*-gvsoc_test/**/wrapper_dynamics_trace.ndjson"))
    trace_candidates += sorted(Path("/tmp/sharc_figure5_tcp").glob("2026-*/**/wrapper_dynamics_trace.ndjson"))

    samples: list[dict[str, Any]] = []
    for trace in trace_candidates:
        for rec in _iter_trace_records(trace):
            samples.append(rec)
            if len(samples) >= max_samples:
                return samples

    if samples:
        return samples

    # Deterministic fallback corpus if no traces are available.
    return [
        {"x": [0.0, 60.0, 15.0], "w": [11.0, 1.0], "u_prev": [0.0, 100.0], "source": "fallback"},
        {"x": [20.0, 55.0, 12.5], "w": [9.0, 1.0], "u_prev": [100.0, 300.0], "source": "fallback"},
        {"x": [75.0, 35.0, 8.0], "w": [6.0, 1.0], "u_prev": [0.0, 1200.0], "source": "fallback"},
    ]


def check_official_static_contract(wrapper_path: Path, server_path: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    server_text = server_path.read_text(encoding="utf-8")

    if '"type": "qp_solve"' not in wrapper_text:
        issues.append("wrapper does not define qp_solve request")
    if '"x": x' not in wrapper_text or '"w": w' not in wrapper_text or '"u_prev": u_prev' not in wrapper_text:
        issues.append("wrapper qp_solve request does not include x/w/u_prev")
    if '"qp_payload"' in wrapper_text:
        issues.append("wrapper contains qp_payload in request path (should send x/w/u_prev)")

    if 'backend="c_abi"' not in server_text:
        issues.append("server host formulation is not pinned to c_abi")
    if "allow_fallback=False" not in server_text:
        issues.append("server host formulation fallback is not disabled")
    if "qp_payload is not allowed in SHARC_OFFICIAL_RISCV_MODE" not in server_text:
        issues.append("server does not reject qp_payload in official mode")
    if "qp_blob_hex is not allowed in SHARC_OFFICIAL_RISCV_MODE" not in server_text:
        issues.append("server does not reject qp_blob_hex in official mode")

    return len(issues) == 0, issues


def check_tcp_log_evidence(log_path: Path) -> tuple[bool, dict[str, Any]]:
    if not log_path.exists():
        return False, {"error": f"log not found: {log_path}", "count": 0}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    pattern = r"qp_solve payload backend=c_abi fields=P,q,A,l,u"
    count = len(re.findall(pattern, text))
    return count > 0, {"count": count, "pattern": pattern, "log_path": str(log_path)}


def run_gate(tol: float, max_samples: int, tcp_log: Path) -> dict[str, Any]:
    sys.path.insert(0, str(SCRIPTS_DIR))
    mpc_host_api = _load_module(SCRIPTS_DIR / "mpc_host_api.py", "mpc_host_api_gate_t3")
    wrapper = _load_module(WRAPPER_PATH, "wrapper_gate_t3")
    qp_payload_mod = _load_module(SCRIPTS_DIR / "qp_payload.py", "qp_payload_gate_t3")

    corpus = build_corpus(max_samples=max_samples)

    max_abs_overall = 0.0
    max_abs_by_field = {k: 0.0 for k in NUM_FIELDS}
    int_mismatches = []
    schema_errors = []
    wrapper_diag_max = 0.0

    for i, rec in enumerate(corpus):
        x = rec["x"]
        w = rec["w"]
        u_prev = rec["u_prev"]

        p_c, backend = mpc_host_api.build_acc_qp_payload_host(
            x,
            u_prev,
            w,
            backend="c_abi",
            allow_fallback=False,
        )
        if backend != "c_abi":
            schema_errors.append({"index": i, "error": f"unexpected backend={backend}"})
            continue
        try:
            blob = qp_payload_mod.encode_qp_message(p_c, request_id=i)
            decoded = qp_payload_mod.decode_qp_message(blob)
            p_export = decoded.get("payload")
        except Exception as exc:
            schema_errors.append({"index": i, "error": f"payload framing round-trip failed: {exc}"})
            continue
        p_w = wrapper.build_acc_qp_payload(x, w, u_prev)  # diagnostic only

        ok_c, err_c = qp_payload_mod.validate_qp_payload(p_c)
        ok_e, err_e = qp_payload_mod.validate_qp_payload(p_export)
        ok_w, err_w = qp_payload_mod.validate_qp_payload(p_w)
        if not ok_c:
            schema_errors.append({"index": i, "error": f"c_abi payload invalid: {err_c}"})
            continue
        if not ok_e:
            schema_errors.append({"index": i, "error": f"export payload invalid: {err_e}"})
            continue
        if not ok_w:
            schema_errors.append({"index": i, "error": f"wrapper payload invalid: {err_w}"})
            continue

        cmp_out = compare_payloads(p_c, p_export)
        if not cmp_out["int_equal"]:
            int_mismatches.append({"index": i, "mismatches": cmp_out["int_mismatches"]})
        for key, val in cmp_out["max_abs_by_field"].items():
            if val > max_abs_by_field[key]:
                max_abs_by_field[key] = val
        if cmp_out["max_abs_overall"] > max_abs_overall:
            max_abs_overall = cmp_out["max_abs_overall"]

        # Diagnostic only (not gating): wrapper python builder drift vs c_abi
        cmp_wrapper = compare_payloads(p_c, p_w)
        if cmp_wrapper["max_abs_overall"] > wrapper_diag_max:
            wrapper_diag_max = cmp_wrapper["max_abs_overall"]

    static_ok, static_issues = check_official_static_contract(WRAPPER_PATH, SERVER_PATH)
    log_ok, log_info = check_tcp_log_evidence(tcp_log)

    pass_parity = (max_abs_overall <= tol) and (len(int_mismatches) == 0) and (len(schema_errors) == 0)
    gate_pass = pass_parity and static_ok and log_ok

    return {
        "pass": gate_pass,
        "tol": tol,
        "samples": len(corpus),
        "parity": {
            "pass": pass_parity,
            "max_abs_overall": max_abs_overall,
            "max_abs_by_field": max_abs_by_field,
            "int_mismatch_count": len(int_mismatches),
            "schema_error_count": len(schema_errors),
            "int_mismatches": int_mismatches[:5],
            "schema_errors": schema_errors[:5],
        },
        "wrapper_diagnostic": {
            "max_abs_overall_vs_c_abi": wrapper_diag_max,
            "note": "diagnostic only; not part of blocking T3 criterion",
        },
        "log_evidence": {
            "pass": log_ok,
            **log_info,
        },
        "official_static_contract": {
            "pass": static_ok,
            "issues": static_issues,
        },
    }


def write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# T3 Formulation Parity Gate",
        "",
        f"- pass: `{report['pass']}`",
        f"- tol: `{report['tol']}`",
        f"- samples: `{report['samples']}`",
        "",
        "## Parity",
        f"- pass: `{report['parity']['pass']}`",
        f"- max_abs_overall: `{report['parity']['max_abs_overall']}`",
        "",
        "| field | max_abs_diff |",
        "|---|---:|",
    ]
    for key, val in report["parity"]["max_abs_by_field"].items():
        lines.append(f"| {key} | {val:.12e} |")

    lines += [
        "",
        "## Log Evidence",
        f"- pass: `{report['log_evidence']['pass']}`",
        f"- count: `{report['log_evidence'].get('count', 0)}`",
        f"- pattern: `{report['log_evidence'].get('pattern', '')}`",
        "",
        "## Wrapper Diagnostic (non-blocking)",
        f"- max_abs_overall_vs_c_abi: `{report['wrapper_diagnostic']['max_abs_overall_vs_c_abi']}`",
        "",
        "## Official Static Contract",
        f"- pass: `{report['official_static_contract']['pass']}`",
    ]
    if report["official_static_contract"]["issues"]:
        lines.append("- issues:")
        for issue in report["official_static_contract"]["issues"]:
            lines.append(f"  - {issue}")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run T3 formulation parity gate.")
    p.add_argument("--tol", type=float, default=1e-12)
    p.add_argument("--max-samples", type=int, default=256)
    p.add_argument("--tcp-log", type=Path, default=DEFAULT_TCP_LOG)
    p.add_argument("--report-json", type=Path, default=DEFAULT_JSON)
    p.add_argument("--report-md", type=Path, default=DEFAULT_MD)
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_gate(tol=args.tol, max_samples=args.max_samples, tcp_log=args.tcp_log)

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_md(report, args.report_md)

    print(json.dumps({"pass": report["pass"], "report_json": str(args.report_json)}, indent=2))
    if report["pass"]:
        print("PASS: T3 formulation parity gate")
        return 0
    print("FAIL: T3 formulation parity gate")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
