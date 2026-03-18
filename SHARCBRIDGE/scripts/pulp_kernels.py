#!/usr/bin/env python3
"""NumPy-based emulator for PULP kernel execution (T5 baseline)."""

from __future__ import annotations

import numpy as np

DTYPE = np.float64


def _cache(payload: dict) -> dict:
    c = payload.get("__pulp_cache")
    if isinstance(c, dict):
        return c
    c = {}
    payload["__pulp_cache"] = c
    return c


def estimate_cycles(op: str, payload: dict, optimized: bool) -> int:
    if op == "dot":
        n = len(payload["x"])
        base = 2 * n
    elif op == "axpy":
        n = len(payload["x"])
        base = 2 * n
    elif op == "box_project":
        n = len(payload["x"])
        base = 3 * n
    elif op == "matvec_dense":
        base = 2 * int(payload["rows"]) * int(payload["cols"])
    elif op == "matvec_sparse":
        base = 2 * len(payload["indices"])
    else:
        raise ValueError(f"unsupported op: {op}")
    factor = 0.62 if optimized else 1.0
    return int(base * factor)


def _dot(payload: dict) -> float:
    c = _cache(payload)
    x = c.get("x")
    y = c.get("y")
    if x is None:
        x = np.asarray(payload["x"], dtype=DTYPE)
        c["x"] = x
    if y is None:
        y = np.asarray(payload["y"], dtype=DTYPE)
        c["y"] = y
    return float(np.dot(x, y))


def _axpy(payload: dict) -> list[float]:
    c = _cache(payload)
    alpha = DTYPE(payload["alpha"])
    x = c.get("x")
    y = c.get("y")
    if x is None:
        x = np.asarray(payload["x"], dtype=DTYPE)
        c["x"] = x
    if y is None:
        y = np.asarray(payload["y"], dtype=DTYPE)
        c["y"] = y
    return (alpha * x + y).astype(DTYPE).tolist()


def _box_project(payload: dict) -> list[float]:
    c = _cache(payload)
    x = c.get("x")
    lo = c.get("lo")
    hi = c.get("hi")
    if x is None:
        x = np.asarray(payload["x"], dtype=DTYPE)
        c["x"] = x
    if lo is None:
        lo = np.asarray(payload["lo"], dtype=DTYPE)
        c["lo"] = lo
    if hi is None:
        hi = np.asarray(payload["hi"], dtype=DTYPE)
        c["hi"] = hi
    return np.clip(x, lo, hi).astype(DTYPE).tolist()


def _matvec_dense(payload: dict) -> list[float]:
    c = _cache(payload)
    rows = int(payload["rows"])
    cols = int(payload["cols"])
    A = c.get("A")
    x = c.get("x")
    if A is None:
        A = np.asarray(payload["A"], dtype=DTYPE).reshape(rows, cols)
        c["A"] = A
    if x is None:
        x = np.asarray(payload["x"], dtype=DTYPE)
        c["x"] = x
    return (A @ x).astype(DTYPE).tolist()


def _matvec_sparse(payload: dict) -> list[float]:
    c = _cache(payload)
    rows = int(payload["rows"])
    cols = int(payload["cols"])
    A = c.get("A_dense")
    x = c.get("x")
    if A is None:
        indptr = payload["indptr"]
        indices = payload["indices"]
        data = payload["data"]
        A = np.zeros((rows, cols), dtype=DTYPE)
        for r in range(rows):
            start = int(indptr[r])
            end = int(indptr[r + 1])
            for i in range(start, end):
                A[r, int(indices[i])] = float(data[i])
        c["A_dense"] = A
    if x is None:
        x = np.asarray(payload["x"], dtype=DTYPE)
        c["x"] = x

    return (A @ x).astype(DTYPE).tolist()


def dispatch_pulp_kernel_op(op: str, payload: dict) -> dict:
    if op == "dot":
        result = _dot(payload)
    elif op == "axpy":
        result = _axpy(payload)
    elif op == "box_project":
        result = _box_project(payload)
    elif op == "matvec_dense":
        result = _matvec_dense(payload)
    elif op == "matvec_sparse":
        result = _matvec_sparse(payload)
    else:
        raise ValueError(f"unsupported op: {op}")

    return {
        "backend": "pulp_emu",
        "result": result,
        "cycles_est": estimate_cycles(op, payload, optimized=True),
    }
