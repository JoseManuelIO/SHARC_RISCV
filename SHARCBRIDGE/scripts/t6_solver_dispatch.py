#!/usr/bin/env python3
"""T6 solver integration using kernel dispatcher (host <-> pulp_emu)."""

from __future__ import annotations

import time
import sys
from pathlib import Path
from typing import Any

_scripts_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))
from kernel_ops import dispatch_kernel_op


DEFAULT_QP_SETTINGS = {
    "max_iter": 60,
    "tol": 1e-3,
    "alpha": 0.05,
}

ACC_PARAMS = {
    "MASS": 2044.0,
    "BETA": 339.1329,
    "GAMMA": 0.77,
    "D_MIN": 6.0,
    "V_DES": 15.0,
    "F_ACCEL_MAX": 4880.0,
    "F_BRAKE_MAX": 6507.0,
    "SAMPLE_TIME": 0.2,
    "MPC_W_DU_BRAKE": 1.0,
    "MPC_W_HEADWAY": 80.0,
}


class KernelDispatcher:
    """Routes kernel ops to selected backend(s) with optional fallback."""

    def __init__(self, backend_map: dict[str, str] | None = None, default_backend: str = "host_fallback"):
        self._backend_map = backend_map or {}
        self._default_backend = default_backend
        self._stats = {
            "total_calls": 0,
            "fallback_calls": 0,
            "cycles_est_total": 0,
            "ops": {},
        }

    def _backend_for(self, op: str) -> str:
        return self._backend_map.get(op, self._default_backend)

    def run(self, op: str, payload: dict[str, Any]) -> Any:
        backend = self._backend_for(op)
        op_stats = self._stats["ops"].setdefault(
            op,
            {
                "calls": 0,
                "fallback_calls": 0,
                "time_s": 0.0,
                "backend_calls": {},
                "cycles_est_total": 0,
            },
        )
        t0 = time.perf_counter()
        try:
            out = dispatch_kernel_op(op, payload, backend=backend)
            used_backend = backend
        except Exception:
            if backend == "host_fallback":
                raise
            out = dispatch_kernel_op(op, payload, backend="host_fallback")
            used_backend = "host_fallback"
            self._stats["fallback_calls"] += 1
            op_stats["fallback_calls"] += 1

        dt = time.perf_counter() - t0
        cycles_est = int(out.get("cycles_est", 0)) if isinstance(out, dict) else 0
        self._stats["total_calls"] += 1
        op_stats["calls"] += 1
        op_stats["time_s"] += dt
        op_stats["backend_calls"][used_backend] = op_stats["backend_calls"].get(used_backend, 0) + 1
        op_stats["cycles_est_total"] += cycles_est
        self._stats["cycles_est_total"] += cycles_est
        return out["result"]

    def snapshot(self) -> dict:
        snap = {
            "total_calls": self._stats["total_calls"],
            "fallback_calls": self._stats["fallback_calls"],
            "cycles_est_total": self._stats["cycles_est_total"],
            "ops": {},
        }
        for op, st in self._stats["ops"].items():
            snap["ops"][op] = {
                "calls": st["calls"],
                "fallback_calls": st["fallback_calls"],
                "time_s": st["time_s"],
                "backend_calls": dict(st["backend_calls"]),
                "cycles_est_total": st["cycles_est_total"],
            }
        return snap


def _friction(v: float, p: dict) -> float:
    return p["BETA"] + p["GAMMA"] * v * v


def build_acc_qp(x: list[float], u_prev: list[float], w: list[float], p: dict | None = None) -> dict:
    p = p or ACC_PARAMS
    wy = 10000.0
    wu = 0.01
    wdu_acc = 1.0
    wdu_br = p["MPC_W_DU_BRAKE"]
    wh = p["MPC_W_HEADWAY"]

    v = float(x[2])
    h = float(x[1])
    sample_time = p["SAMPLE_TIME"]
    mass = p["MASS"]
    a = sample_time / mass
    c_v = v - a * _friction(v, p)
    gv = [a, -a]
    ev = c_v - p["V_DES"]
    c_h = h + sample_time * (w[0] - c_v)
    gh = [-sample_time * a, sample_time * a]
    eh = c_h - p["D_MIN"]

    P = [0.0, 0.0, 0.0, 0.0]
    q = [0.0, 0.0]

    # velocity cost
    P[0] += 2.0 * wy * gv[0] * gv[0]
    P[1] += 2.0 * wy * gv[0] * gv[1]
    P[2] += 2.0 * wy * gv[1] * gv[0]
    P[3] += 2.0 * wy * gv[1] * gv[1]
    q[0] += 2.0 * wy * ev * gv[0]
    q[1] += 2.0 * wy * ev * gv[1]

    # headway shaping
    P[0] += 2.0 * wh * gh[0] * gh[0]
    P[1] += 2.0 * wh * gh[0] * gh[1]
    P[2] += 2.0 * wh * gh[1] * gh[0]
    P[3] += 2.0 * wh * gh[1] * gh[1]
    q[0] += 2.0 * wh * eh * gh[0]
    q[1] += 2.0 * wh * eh * gh[1]

    # input and delta-input costs
    P[0] += 2.0 * (wu + wdu_acc)
    P[3] += 2.0 * (wu + wdu_br)
    q[0] += -2.0 * wdu_acc * u_prev[0]
    q[1] += -2.0 * wdu_br * u_prev[1]

    l = [0.0, 0.0]
    u = [p["F_ACCEL_MAX"], p["F_BRAKE_MAX"]]
    x0 = [min(max(u_prev[0], l[0]), u[0]), min(max(u_prev[1], l[1]), u[1])]
    return {"P": P, "q": q, "l": l, "u": u, "x0": x0}


def solve_qp_with_dispatch(
    P: list[float],
    q: list[float],
    l: list[float],
    u: list[float],
    x0: list[float],
    dispatcher: KernelDispatcher,
    settings: dict | None = None,
) -> dict:
    settings = settings or DEFAULT_QP_SETTINGS
    n = len(q)
    x = [float(v) for v in x0]
    max_iter = int(settings["max_iter"])
    tol = float(settings["tol"])
    alpha = float(settings["alpha"])

    x = dispatcher.run("box_project", {"x": x, "lo": l, "hi": u})

    def _objective(xv: list[float]) -> float:
        Px = dispatcher.run("matvec_dense", {"rows": n, "cols": n, "A": P, "x": xv})
        lin = dispatcher.run("dot", {"x": q, "y": xv})
        quad = dispatcher.run("dot", {"x": xv, "y": Px})
        return float(lin + 0.5 * quad)

    for it in range(max_iter):
        Px = dispatcher.run("matvec_dense", {"rows": n, "cols": n, "A": P, "x": x})
        grad = dispatcher.run("axpy", {"alpha": 1.0, "x": Px, "y": q})
        grad_norm_sq = float(dispatcher.run("dot", {"x": grad, "y": grad}))
        obj_current = _objective(x)

        if grad_norm_sq < tol * tol:
            return {
                "x": x,
                "obj_val": obj_current,
                "iterations": it,
                "converged": 1,
                "dispatcher": dispatcher.snapshot(),
            }

        step = alpha
        accepted = False
        for _ in range(20):
            x_new = dispatcher.run("axpy", {"alpha": -step, "x": grad, "y": x})
            x_new = dispatcher.run("box_project", {"x": x_new, "lo": l, "hi": u})
            obj_new = _objective(x_new)

            diff = dispatcher.run("axpy", {"alpha": -1.0, "x": x_new, "y": x})
            decrease = float(dispatcher.run("dot", {"x": grad, "y": diff}))
            if obj_new <= obj_current - 0.1 * decrease:
                x = x_new
                accepted = True
                break
            step *= 0.5

        if not accepted:
            x = x_new

    return {
        "x": x,
        "obj_val": _objective(x),
        "iterations": max_iter,
        "converged": 0,
        "dispatcher": dispatcher.snapshot(),
    }


def solve_acc_step_with_dispatch(
    x: list[float],
    u_prev: list[float],
    w: list[float],
    dispatcher: KernelDispatcher,
    settings: dict | None = None,
) -> dict:
    qp = build_acc_qp(x, u_prev, w, ACC_PARAMS)
    out = solve_qp_with_dispatch(qp["P"], qp["q"], qp["l"], qp["u"], qp["x0"], dispatcher, settings=settings)
    return {
        "u": out["x"],
        "cost": out["obj_val"],
        "iterations": out["iterations"],
        "converged": out["converged"],
        "dispatcher": out["dispatcher"],
    }
