#!/usr/bin/env python3
"""Kernel operation contracts and host fallback implementations."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_scripts_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))


KERNEL_SPECS = {
    "matvec_dense": {
        "required": ["rows", "cols", "A", "x"],
        "notes": "A is row-major dense matrix flattened; float32-compatible payload.",
    },
    "matvec_sparse": {
        "required": ["rows", "cols", "indptr", "indices", "data", "x"],
        "notes": "CSR format; indptr length rows+1; indices/data length nnz.",
    },
    "dot": {
        "required": ["x", "y"],
        "notes": "Inner product of two vectors with same length.",
    },
    "axpy": {
        "required": ["alpha", "x", "y"],
        "notes": "Computes alpha*x + y.",
    },
    "box_project": {
        "required": ["x", "lo", "hi"],
        "notes": "Element-wise projection: min(max(x, lo), hi).",
    },
}


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_number_list(v: Any) -> bool:
    return isinstance(v, list) and all(_is_number(x) for x in v)


def validate_kernel_payload(op: str, payload: Any) -> tuple[bool, str]:
    if op not in KERNEL_SPECS:
        return False, f"unsupported op: {op}"
    if not isinstance(payload, dict):
        return False, "payload must be object"

    for key in KERNEL_SPECS[op]["required"]:
        if key not in payload:
            return False, f"missing payload field: {key}"

    if op == "dot":
        x, y = payload["x"], payload["y"]
        if not _is_number_list(x) or not _is_number_list(y):
            return False, "dot expects numeric vectors x and y"
        if len(x) != len(y):
            return False, "dot expects len(x) == len(y)"
        return True, ""

    if op == "axpy":
        alpha, x, y = payload["alpha"], payload["x"], payload["y"]
        if not _is_number(alpha):
            return False, "axpy expects numeric alpha"
        if not _is_number_list(x) or not _is_number_list(y):
            return False, "axpy expects numeric vectors x and y"
        if len(x) != len(y):
            return False, "axpy expects len(x) == len(y)"
        return True, ""

    if op == "box_project":
        x, lo, hi = payload["x"], payload["lo"], payload["hi"]
        if not _is_number_list(x) or not _is_number_list(lo) or not _is_number_list(hi):
            return False, "box_project expects numeric vectors x/lo/hi"
        if len(x) != len(lo) or len(x) != len(hi):
            return False, "box_project expects matching vector lengths"
        for lv, hv in zip(lo, hi):
            if lv > hv:
                return False, "box_project expects lo[i] <= hi[i]"
        return True, ""

    if op == "matvec_dense":
        rows, cols = payload["rows"], payload["cols"]
        A, x = payload["A"], payload["x"]
        if not isinstance(rows, int) or not isinstance(cols, int) or rows <= 0 or cols <= 0:
            return False, "matvec_dense expects rows/cols positive ints"
        if not _is_number_list(A) or not _is_number_list(x):
            return False, "matvec_dense expects numeric A and x"
        if len(A) != rows * cols:
            return False, "matvec_dense expects len(A) == rows*cols"
        if len(x) != cols:
            return False, "matvec_dense expects len(x) == cols"
        return True, ""

    # op == matvec_sparse
    rows, cols = payload["rows"], payload["cols"]
    indptr, indices, data, x = payload["indptr"], payload["indices"], payload["data"], payload["x"]
    if not isinstance(rows, int) or not isinstance(cols, int) or rows <= 0 or cols <= 0:
        return False, "matvec_sparse expects rows/cols positive ints"
    if not isinstance(indptr, list) or not all(isinstance(v, int) for v in indptr):
        return False, "matvec_sparse expects integer indptr"
    if not isinstance(indices, list) or not all(isinstance(v, int) for v in indices):
        return False, "matvec_sparse expects integer indices"
    if not _is_number_list(data) or not _is_number_list(x):
        return False, "matvec_sparse expects numeric data and x"
    if len(indptr) != rows + 1:
        return False, "matvec_sparse expects len(indptr) == rows+1"
    if len(indices) != len(data):
        return False, "matvec_sparse expects len(indices) == len(data)"
    if len(x) != cols:
        return False, "matvec_sparse expects len(x) == cols"
    if indptr[0] != 0 or indptr[-1] != len(indices):
        return False, "matvec_sparse expects CSR boundaries indptr[0]=0 and indptr[-1]=nnz"
    if any(v < 0 for v in indices) or any(v >= cols for v in indices):
        return False, "matvec_sparse index out of bounds"
    return True, ""


def _matvec_dense(rows: int, cols: int, A: list[float], x: list[float]) -> list[float]:
    out = [0.0] * rows
    for r in range(rows):
        base = r * cols
        acc = 0.0
        for c in range(cols):
            acc += float(A[base + c]) * float(x[c])
        out[r] = acc
    return out


def _matvec_sparse(rows: int, indptr: list[int], indices: list[int], data: list[float], x: list[float]) -> list[float]:
    out = [0.0] * rows
    for r in range(rows):
        acc = 0.0
        start, end = indptr[r], indptr[r + 1]
        for i in range(start, end):
            acc += float(data[i]) * float(x[indices[i]])
        out[r] = acc
    return out


def dispatch_kernel_op(op: str, payload: dict, backend: str = "host_fallback") -> dict:
    ok, error = validate_kernel_payload(op, payload)
    if not ok:
        raise ValueError(error)

    if backend == "pulp_emu":
        from pulp_kernels import dispatch_pulp_kernel_op

        out = dispatch_pulp_kernel_op(op, payload)
        return {"op": op, **out}

    if backend != "host_fallback":
        raise ValueError(f"unsupported backend: {backend}")

    if op == "dot":
        x, y = payload["x"], payload["y"]
        result = sum(float(a) * float(b) for a, b in zip(x, y))
    elif op == "axpy":
        alpha, x, y = float(payload["alpha"]), payload["x"], payload["y"]
        result = [alpha * float(a) + float(b) for a, b in zip(x, y)]
    elif op == "box_project":
        x, lo, hi = payload["x"], payload["lo"], payload["hi"]
        result = [min(max(float(v), float(lv)), float(hv)) for v, lv, hv in zip(x, lo, hi)]
    elif op == "matvec_dense":
        result = _matvec_dense(payload["rows"], payload["cols"], payload["A"], payload["x"])
    elif op == "matvec_sparse":
        result = _matvec_sparse(payload["rows"], payload["indptr"], payload["indices"], payload["data"], payload["x"])
    else:
        raise ValueError(f"unsupported op: {op}")

    return {"op": op, "result": result, "backend": "host_fallback"}
