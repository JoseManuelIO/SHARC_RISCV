#!/usr/bin/env python3
"""Python port of SHARCBRIDGE/mpc/mpc_acc_controller.c solve_mpc path."""

from __future__ import annotations

import numpy as np

MASS = 2044.0
BETA = 339.1329
GAMMA = 0.77
D_MIN = 6.0
V_DES = 15.0
V_MAX = 20.0
F_ACCEL_MAX = 4880.0
F_BRAKE_MAX = 6507.0
SAMPLE_TIME = 0.2
A_BRAKE_EGO = 3.2
A_BRAKE_FRONT = 5.0912
PREDICTION_HORIZON = 5

MPC_W_DU_BRAKE = 1.0
MPC_W_HEADWAY = 80.0
MPC_MARGIN_TRIGGER = -1.0
MPC_SAFETY_CLOSE_GAIN = 185.0
MPC_SAFETY_MARGIN_GAIN = 28.0
MPC_BRAKE_CAP_MARGIN_POS = 4.0
MPC_BRAKE_CAP_BASE = 900.0
MPC_BRAKE_CAP_SPEED_GAIN = 230.0
MPC_BRAKE_CAP_MARGIN_SLOPE = 18.0
MPC_BRAKE_CAP_MIN = 150.0
MPC_BRAKE_CAP_MAX = 2400.0
MPC_TRANSITION_GUARD_ENABLE = False
MPC_TRANSITION_H_MIN = 40.0
MPC_TRANSITION_H_MAX = 47.0
MPC_TRANSITION_VDIFF_MIN = 1.2
MPC_TRANSITION_BRAKE_K = 260.0
MPC_TRANSITION_BRAKE_B = 250.0


def _f(v: float) -> float:
    """Force IEEE-754 single-precision rounding like C float."""
    return float(np.float32(v))


def _clip(v: float, lo: float, hi: float) -> float:
    return _f(lo if v < lo else hi if v > hi else v)


def compute_friction(v: float) -> float:
    return _f(BETA + GAMMA * v * v)


def predict_state(x: list[float], u: list[float], w: list[float], dt: float) -> list[float]:
    v = _f(x[2])
    friction = compute_friction(v)
    a = _f((_f(u[0]) - _f(u[1]) - friction) / MASS)
    v_next = _clip(v + a * dt, 0.0, V_MAX)
    return [
        _f(x[0] + v_next * dt),
        _f(max(0.0, _f(x[1]) + (_f(w[0]) - v_next) * dt)),
        v_next,
    ]


def predict_terminal_margin(x0: list[float], u: list[float], w0: list[float]) -> tuple[float, float]:
    x = [x0[0], x0[1], x0[2]]
    vf_end = _f(w0[0])

    for k in range(PREDICTION_HORIZON):
        vf_end = _f(max(0.0, _f(w0[0]) - _f(float(k) * SAMPLE_TIME * A_BRAKE_FRONT)))
        x = predict_state(x, u, [vf_end, 1.0], SAMPLE_TIME)

    lhs = _f(x[1] - x[2] * (V_MAX / (2.0 * A_BRAKE_EGO)))
    rhs = _f(D_MIN - (vf_end * vf_end) / (2.0 * A_BRAKE_FRONT))
    closing_end = _f(x[2] - vf_end)
    return _f(lhs - rhs), closing_end


def _project_box(x: list[float], l: list[float], u: list[float]) -> None:
    for i in range(len(x)):
        if x[i] < l[i]:
            x[i] = _f(l[i])
        if x[i] > u[i]:
            x[i] = _f(u[i])


def _cholesky_decompose(A: list[float], n: int) -> list[float] | None:
    L = [_f(0.0)] * (n * n)
    for i in range(n):
        for j in range(i + 1):
            acc = _f(A[i * n + j])
            for k in range(j):
                acc = _f(acc - _f(L[i * n + k]) * _f(L[j * n + k]))
            if i == j:
                if acc <= _f(1e-12):
                    return None
                L[i * n + j] = _f(np.sqrt(acc))
            else:
                L[i * n + j] = _f(acc / _f(L[j * n + j]))
    return L


def _cholesky_solve(L: list[float], b: list[float], n: int) -> list[float]:
    y = [_f(0.0)] * n
    x = [_f(0.0)] * n

    for i in range(n):
        acc = _f(b[i])
        for j in range(i):
            acc = _f(acc - _f(L[i * n + j]) * _f(y[j]))
        y[i] = _f(acc / _f(L[i * n + i]))

    for i in range(n - 1, -1, -1):
        acc = _f(y[i])
        for j in range(i + 1, n):
            acc = _f(acc - _f(L[j * n + i]) * _f(x[j]))
        x[i] = _f(acc / _f(L[i * n + i]))

    return x


def _objective(P: list[float], q: list[float], x: list[float], n: int) -> float:
    obj = _f(0.0)
    for i in range(n):
        obj = _f(obj + _f(q[i]) * _f(x[i]))
    for i in range(n):
        px = _f(0.0)
        base = i * n
        for j in range(n):
            px = _f(px + _f(P[base + j]) * _f(x[j]))
        obj = _f(obj + _f(0.5) * _f(x[i]) * px)
    return _f(obj)


def qp_solve(
    P: list[float],
    q: list[float],
    l: list[float],
    u: list[float],
    x: list[float],
    max_iter: int = 60,
    tol: float = 1e-3,
    alpha: float = 0.05,
) -> tuple[list[float], float, int, int]:
    n = len(x)
    if n <= 0:
        return x, _f(0.0), 0, 0

    rho = _f(alpha if alpha > 0.0 else 0.05)
    if rho < _f(1e-6):
        rho = _f(1e-6)

    K = [_f(0.0)] * (n * n)
    for i in range(n):
        base = i * n
        for j in range(n):
            K[base + j] = _f(P[base + j])
        K[base + i] = _f(K[base + i] + rho)

    L = _cholesky_decompose(K, n)
    if L is None:
        return x, _objective(P, q, x, n), 0, 0

    _project_box(x, l, u)
    z = [_f(v) for v in x]
    y = [_f(0.0)] * n

    for it in range(max_iter):
        rhs = [_f(0.0)] * n
        for i in range(n):
            rhs[i] = _f(_f(rho * _f(_f(z[i]) - _f(y[i]))) - _f(q[i]))
        x = _cholesky_solve(L, rhs, n)

        z_prev = list(z)
        r_norm_sq = _f(0.0)
        s_norm_sq = _f(0.0)
        for i in range(n):
            z_i = _f(_f(x[i]) + _f(y[i]))
            if z_i < l[i]:
                z_i = _f(l[i])
            if z_i > u[i]:
                z_i = _f(u[i])
            z[i] = z_i
            y[i] = _f(_f(y[i]) + _f(_f(x[i]) - _f(z[i])))

            r_i = _f(_f(x[i]) - _f(z[i]))
            s_i = _f(rho * _f(_f(z[i]) - _f(z_prev[i])))
            r_norm_sq = _f(r_norm_sq + _f(r_i * r_i))
            s_norm_sq = _f(s_norm_sq + _f(s_i * s_i))

        if r_norm_sq <= _f(tol * tol) and s_norm_sq <= _f(tol * tol):
            x = list(z)
            return x, _objective(P, q, x, n), it + 1, 1

    x = list(z)
    return x, _objective(P, q, x, n), max_iter, 0


def solve_mpc(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    wy = _f(10000.0)
    wu = _f(0.01)
    wdu_acc = _f(1.0)
    wdu_br = _f(MPC_W_DU_BRAKE)

    v = _f(x[2])
    h = _f(x[1])
    friction = compute_friction(v)

    a = _f(SAMPLE_TIME / MASS)
    c_v = _f(v - a * friction)
    gv = [_f(a), _f(-a)]
    ev = _f(c_v - V_DES)

    c_h = _f(h + SAMPLE_TIME * (_f(w[0]) - c_v))
    gh = [_f(-SAMPLE_TIME * a), _f(SAMPLE_TIME * a)]
    eh = _f(c_h - D_MIN)

    P = [0.0, 0.0, 0.0, 0.0]
    q = [0.0, 0.0]

    P[0] = _f(P[0] + _f(2.0) * wy * gv[0] * gv[0])
    P[1] = _f(P[1] + _f(2.0) * wy * gv[0] * gv[1])
    P[2] = _f(P[2] + _f(2.0) * wy * gv[1] * gv[0])
    P[3] = _f(P[3] + _f(2.0) * wy * gv[1] * gv[1])
    q[0] = _f(q[0] + _f(2.0) * wy * ev * gv[0])
    q[1] = _f(q[1] + _f(2.0) * wy * ev * gv[1])

    wh = _f(MPC_W_HEADWAY)
    P[0] = _f(P[0] + _f(2.0) * wh * gh[0] * gh[0])
    P[1] = _f(P[1] + _f(2.0) * wh * gh[0] * gh[1])
    P[2] = _f(P[2] + _f(2.0) * wh * gh[1] * gh[0])
    P[3] = _f(P[3] + _f(2.0) * wh * gh[1] * gh[1])
    q[0] = _f(q[0] + _f(2.0) * wh * eh * gh[0])
    q[1] = _f(q[1] + _f(2.0) * wh * eh * gh[1])

    P[0] = _f(P[0] + _f(2.0) * _f(wu + wdu_acc))
    P[3] = _f(P[3] + _f(2.0) * _f(wu + wdu_br))
    q[0] = _f(q[0] + _f(-2.0) * wdu_acc * _f(u_prev[0]))
    q[1] = _f(q[1] + _f(-2.0) * wdu_br * _f(u_prev[1]))

    lo = [0.0, 0.0]
    hi = [F_ACCEL_MAX, F_BRAKE_MAX]
    sol = [_clip(u_prev[0], 0.0, F_ACCEL_MAX), _clip(u_prev[1], 0.0, F_BRAKE_MAX)]

    sol, cost, iters, converged = qp_solve(P, q, lo, hi, sol, max_iter=60, tol=1e-3, alpha=0.05)

    margin, closing_end = predict_terminal_margin(x, sol, w)

    if margin < MPC_MARGIN_TRIGGER and closing_end > 0.0:
        safety_floor = _f(MPC_SAFETY_CLOSE_GAIN * closing_end + MPC_SAFETY_MARGIN_GAIN * (-margin))
        safety_floor = _clip(safety_floor, 0.0, F_BRAKE_MAX)
        sol[1] = max(sol[1], safety_floor)
        sol[0] = 0.0

    if (
        MPC_TRANSITION_GUARD_ENABLE
        and h > MPC_TRANSITION_H_MIN
        and h < MPC_TRANSITION_H_MAX
        and v > (w[0] + MPC_TRANSITION_VDIFF_MIN)
    ):
        v_diff = _f(v - _f(w[0]))
        transition_floor = _f(MPC_TRANSITION_BRAKE_K * v_diff + MPC_TRANSITION_BRAKE_B)
        transition_floor = _clip(transition_floor, 0.0, F_BRAKE_MAX)
        sol[1] = max(sol[1], transition_floor)
        sol[0] = 0.0

    if margin > MPC_BRAKE_CAP_MARGIN_POS and closing_end <= 0.0:
        brake_cap = _f(
            MPC_BRAKE_CAP_BASE
            + MPC_BRAKE_CAP_SPEED_GAIN * max(0.0, _f(v - 8.0))
            - MPC_BRAKE_CAP_MARGIN_SLOPE * _f(margin - MPC_BRAKE_CAP_MARGIN_POS)
        )
        brake_cap = _clip(brake_cap, MPC_BRAKE_CAP_MIN, MPC_BRAKE_CAP_MAX)
        sol[1] = min(sol[1], brake_cap)

    return {
        "u": sol,
        "cost": cost,
        "iterations": iters,
        "converged": converged,
        "margin": margin,
        "closing_end": closing_end,
    }


def solve_acc_step_legacy_python(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    return solve_mpc(x, u_prev, w)
