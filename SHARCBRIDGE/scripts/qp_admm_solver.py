#!/usr/bin/env python3
"""Lightweight deterministic ADMM QP solver for payloads in T2 CSC format.

Problem form:
  minimize 0.5 * x' P x + q' x
  subject to l <= A x <= u
"""

from __future__ import annotations

import math
from typing import Any

from qp_payload import validate_qp_payload


def _csc_to_dense(rows: int, cols: int, colptr: list[int], rowind: list[int], data: list[float]) -> list[list[float]]:
    out = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for c in range(cols):
        for p in range(colptr[c], colptr[c + 1]):
            r = rowind[p]
            out[r][c] += float(data[p])
    return out


def _symmetrize_psd(P_raw: list[list[float]]) -> list[list[float]]:
    n = len(P_raw)
    P = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        P[i][i] = float(P_raw[i][i])
    for i in range(n):
        for j in range(i + 1, n):
            a = float(P_raw[i][j])
            b = float(P_raw[j][i])
            if a != 0.0 and b != 0.0:
                v = 0.5 * (a + b)
            elif a != 0.0:
                v = a
            else:
                v = b
            P[i][j] = v
            P[j][i] = v
    return P


def _matvec(A: list[list[float]], x: list[float]) -> list[float]:
    return [sum(aij * xj for aij, xj in zip(row, x)) for row in A]


def _mat_t_vec(A: list[list[float]], y: list[float]) -> list[float]:
    rows = len(A)
    cols = len(A[0]) if rows else 0
    out = [0.0 for _ in range(cols)]
    for r in range(rows):
        yr = y[r]
        row = A[r]
        for c in range(cols):
            out[c] += row[c] * yr
    return out


def _clip_vec(v: list[float], lo: list[float], hi: list[float]) -> list[float]:
    return [lo[i] if v[i] < lo[i] else hi[i] if v[i] > hi[i] else v[i] for i in range(len(v))]


def _vec_sub(a: list[float], b: list[float]) -> list[float]:
    return [x - y for x, y in zip(a, b)]


def _vec_add(a: list[float], b: list[float]) -> list[float]:
    return [x + y for x, y in zip(a, b)]


def _vec_norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _objective(P: list[list[float]], q: list[float], x: list[float]) -> float:
    quad = 0.0
    for i, xi in enumerate(x):
        quad += xi * sum(P[i][j] * x[j] for j in range(len(x)))
    lin = sum(qi * xi for qi, xi in zip(q, x))
    return 0.5 * quad + lin


def _cholesky_decompose(A: list[list[float]], eps: float = 1e-10) -> list[list[float]] | None:
    n = len(A)
    L = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = A[i][j]
            for k in range(j):
                s -= L[i][k] * L[j][k]
            if i == j:
                if s <= eps:
                    return None
                L[i][j] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return L


def _cholesky_solve(L: list[list[float]], b: list[float]) -> list[float]:
    n = len(L)
    y = [0.0 for _ in range(n)]
    x = [0.0 for _ in range(n)]

    for i in range(n):
        s = b[i]
        for k in range(i):
            s -= L[i][k] * y[k]
        y[i] = s / L[i][i]

    for i in range(n - 1, -1, -1):
        s = y[i]
        for k in range(i + 1, n):
            s -= L[k][i] * x[k]
        x[i] = s / L[i][i]
    return x


def solve_qp_payload(payload: dict, settings: dict | None = None) -> dict[str, Any]:
    ok, err = validate_qp_payload(payload)
    if not ok:
        raise ValueError(err)

    settings = settings or {}
    max_iter = int(settings.get("max_iter", 200))
    tol = float(settings.get("tol", 1e-5))
    rho = float(settings.get("rho", 0.1))
    sigma = float(settings.get("sigma", 1e-8))

    if max_iter <= 0:
        raise ValueError("max_iter must be > 0")
    if tol <= 0:
        raise ValueError("tol must be > 0")
    if rho <= 0:
        raise ValueError("rho must be > 0")
    if sigma < 0:
        raise ValueError("sigma must be >= 0")

    n = int(payload["n"])
    m = int(payload["m"])
    q = [float(v) for v in payload["q"]]
    l = [float(v) for v in payload["l"]]
    u = [float(v) for v in payload["u"]]

    P_raw = _csc_to_dense(
        rows=n,
        cols=n,
        colptr=payload["P_colptr"],
        rowind=payload["P_rowind"],
        data=payload["P_data"],
    )
    A = _csc_to_dense(
        rows=m,
        cols=n,
        colptr=payload["A_colptr"],
        rowind=payload["A_rowind"],
        data=payload["A_data"],
    )
    P = _symmetrize_psd(P_raw)

    # K = P + rho A^T A + sigma I
    AtA = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            AtA[i][j] = sum(A[k][i] * A[k][j] for k in range(m))
    K = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            K[i][j] = P[i][j] + rho * AtA[i][j]
        K[i][i] += sigma

    L = _cholesky_decompose(K)
    if L is None:
        raise ValueError("KKT factorization failed (matrix not SPD)")

    x = [0.0 for _ in range(n)]
    Ax = _matvec(A, x)
    z = _clip_vec(Ax, l, u)
    y = [0.0 for _ in range(m)]

    primal_res = float("inf")
    dual_res = float("inf")
    converged = 0
    iterations = max_iter

    for it in range(max_iter):
        z_minus_y = _vec_sub(z, y)
        rhs = _mat_t_vec(A, [rho * v for v in z_minus_y])
        for i in range(n):
            rhs[i] -= q[i]
        x = _cholesky_solve(L, rhs)

        Ax = _matvec(A, x)
        z_prev = z
        z = _clip_vec(_vec_add(Ax, y), l, u)
        y = _vec_add(y, _vec_sub(Ax, z))

        r = _vec_sub(Ax, z)
        s = [rho * v for v in _mat_t_vec(A, _vec_sub(z, z_prev))]
        primal_res = _vec_norm(r)
        dual_res = _vec_norm(s)

        if primal_res <= tol and dual_res <= tol:
            converged = 1
            iterations = it + 1
            break

    obj = _objective(P, q, x)
    status = "OPTIMAL" if converged else "MAX_ITER"
    return {
        "status": status,
        "x": x,
        "cost": obj,
        "iterations": iterations,
        "converged": converged,
        "primal_residual": primal_res,
        "dual_residual": dual_res,
        "n": n,
        "m": m,
    }
