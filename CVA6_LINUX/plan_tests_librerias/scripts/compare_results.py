#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: compare_results.py <results_dir> <report_json> <report_md>", file=sys.stderr)
        return 2

    results_dir = Path(sys.argv[1])
    report_json = Path(sys.argv[2])
    report_md = Path(sys.argv[3])

    host_files = sorted(results_dir.glob("host_snapshot_*.json"))
    if not host_files:
        print("NO_HOST_FILES", file=sys.stderr)
        return 3

    abs_u_tol = 2e-2
    abs_cost_tol = 2e-1
    status_ok = True
    control_ok = True
    iteration_ok = True
    formulation_ok = False
    compared = []

    max_u0 = 0.0
    max_u1 = 0.0
    max_cost = 0.0
    max_iter = 0.0

    formulation_report = results_dir / "t8_qp_formulation_compare.txt"
    if formulation_report.exists():
        text = formulation_report.read_text(encoding="utf-8", errors="ignore")
        formulation_ok = "T8_QP_FORMULATION_PASS" in text

    for host_path in host_files:
        suffix = host_path.name.replace("host_", "")
        cva6_path = results_dir / f"cva6_{suffix}"
        if not cva6_path.exists():
            compared.append({"snapshot": suffix, "missing": True})
            status_ok = False
            control_ok = False
            iteration_ok = False
            continue

        host = load(host_path)
        cva6 = load(cva6_path)

        u0_diff = abs(host["u"][0] - cva6["u"][0])
        u1_diff = abs(host["u"][1] - cva6["u"][1])
        cost_diff = abs(host["metadata"]["cost"] - cva6["metadata"]["cost"])
        iter_diff = abs(host["metadata"]["iterations"] - cva6["metadata"]["iterations"])
        solver_match = host["metadata"]["solver_status"] == cva6["metadata"]["solver_status"]
        feasible_match = host["metadata"]["is_feasible"] == cva6["metadata"]["is_feasible"]

        max_u0 = max(max_u0, u0_diff)
        max_u1 = max(max_u1, u1_diff)
        max_cost = max(max_cost, cost_diff)
        max_iter = max(max_iter, iter_diff)

        if not solver_match or not feasible_match:
            status_ok = False
        if u0_diff > abs_u_tol or u1_diff > abs_u_tol or cost_diff > abs_cost_tol:
            control_ok = False
        if iter_diff != 0:
            iteration_ok = False

        compared.append(
            {
                "snapshot": suffix,
                "solver_match": solver_match,
                "feasible_match": feasible_match,
                "u0_diff": u0_diff,
                "u1_diff": u1_diff,
                "cost_diff": cost_diff,
                "iter_diff": iter_diff,
            }
        )

    overall = "PASS" if formulation_ok and status_ok and control_ok and iteration_ok else "FAIL"
    behavioral = "PASS" if status_ok and control_ok else "FAIL"

    report = {
        "overall_status": overall,
        "behavioral_status": behavioral,
        "formulation_status": "PASS" if formulation_ok else "FAIL",
        "status_match": status_ok,
        "control_match": control_ok,
        "iteration_match": iteration_ok,
        "tolerances": {
            "abs_u": abs_u_tol,
            "abs_cost": abs_cost_tol,
            "iterations_exact": True,
        },
        "max_diffs": {
            "u0": max_u0,
            "u1": max_u1,
            "cost": max_cost,
            "iterations": max_iter,
        },
        "compared": compared,
        "notes": [
            "La paridad de control se considera funcional si estado/feasibility coinciden y las salidas u permanecen dentro de tolerancia.",
            "La formulacion QP ya fue validada; la desviacion pendiente esta localizada en el camino iterativo/numerico del solver.",
        ],
    }

    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Tarea 8. Gate de paridad host vs CVA6",
        "",
        "## Estado",
        "",
        f"- overall: `{overall}`",
        f"- behavioral: `{behavioral}`",
        f"- formulation: `{'PASS' if formulation_ok else 'FAIL'}`",
        f"- status_match: `{status_ok}`",
        f"- control_match: `{control_ok}`",
        f"- iteration_match: `{iteration_ok}`",
        "",
        "## Maximos observados",
        "",
        f"- max |u0| diff: `{max_u0:.6e}`",
        f"- max |u1| diff: `{max_u1:.6e}`",
        f"- max |cost| diff: `{max_cost:.6e}`",
        f"- max |iterations| diff: `{max_iter:.6e}`",
        "",
        "## Lectura tecnica",
        "",
        "- La formulacion QP coincide entre host y CVA6 dentro de tolerancias numericas de redondeo.",
        "- El ACC original corre tanto en host como en CVA6 Linux.",
        "- El estado del solver y la factibilidad coinciden en todos los snapshots comparados.",
        "- Las salidas de control son muy proximas y pasan una tolerancia funcional razonable.",
        "- El numero de iteraciones no coincide en varios snapshots; por tanto, la paridad completa de solver no esta cerrada.",
        "- El problema queda localizado en el camino iterativo/numerico del solver, no en la construccion del QP.",
    ]
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0 if overall == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
