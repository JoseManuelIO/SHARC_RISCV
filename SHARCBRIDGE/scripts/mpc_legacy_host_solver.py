#!/usr/bin/env python3
"""ctypes bridge for the legacy MPC step solver implemented in C."""

from __future__ import annotations

import ctypes
import os
import subprocess
import tempfile
import threading
from pathlib import Path


_SRC = Path(__file__).with_name("mpc_legacy_host_solver.c")
_BUILD_DIR = Path(os.getenv("SHARC_MPC_SOLVER_BUILD_DIR", tempfile.gettempdir())) / "sharc_mpc_solver"
_SO = _BUILD_DIR / "libmpc_legacy_host_solver.so"
_CC = os.getenv("CC", "gcc")

_LOAD_LOCK = threading.Lock()
_LIB = None


def _compile_shared_library() -> Path:
    _BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if _SO.exists() and _SO.stat().st_mtime >= _SRC.stat().st_mtime:
        return _SO

    cmd = [
        _CC,
        "-std=c99",
        "-O2",
        "-fPIC",
        "-fno-fast-math",
        "-ffp-contract=off",
        "-shared",
        str(_SRC),
        "-lm",
        "-o",
        str(_SO),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "unknown compiler error"
        raise RuntimeError(f"failed to compile {_SRC.name}: {stderr}")
    return _SO


def _load_lib():
    global _LIB
    if _LIB is not None:
        return _LIB
    with _LOAD_LOCK:
        if _LIB is not None:
            return _LIB
        so_path = _compile_shared_library()
        lib = ctypes.CDLL(str(so_path))
        lib.solve_mpc_step.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # x[3]
            ctypes.POINTER(ctypes.c_float),  # u_prev[2]
            ctypes.POINTER(ctypes.c_float),  # w[2]
            ctypes.POINTER(ctypes.c_float),  # u_out[2]
            ctypes.POINTER(ctypes.c_float),  # cost_out
            ctypes.POINTER(ctypes.c_int),  # iters_out
            ctypes.POINTER(ctypes.c_int),  # converged_out
        ]
        lib.solve_mpc_step.restype = ctypes.c_int
        lib.build_acc_qp_matrices.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # x[3]
            ctypes.POINTER(ctypes.c_float),  # u_prev[2]
            ctypes.POINTER(ctypes.c_float),  # w[2]
            ctypes.POINTER(ctypes.c_float),  # P_out[4] (row-major 2x2)
            ctypes.POINTER(ctypes.c_float),  # q_out[2]
            ctypes.POINTER(ctypes.c_float),  # l_out[2]
            ctypes.POINTER(ctypes.c_float),  # u_out[2]
        ]
        lib.build_acc_qp_matrices.restype = ctypes.c_int
        _LIB = lib
        return _LIB


def solve_acc_step_legacy_host(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    lib = _load_lib()

    x_arr = (ctypes.c_float * 3)(float(x[0]), float(x[1]), float(x[2]))
    u_prev_arr = (ctypes.c_float * 2)(float(u_prev[0]), float(u_prev[1]))
    w_arr = (ctypes.c_float * 2)(float(w[0]), float(w[1]))
    u_out_arr = (ctypes.c_float * 2)(0.0, 0.0)
    cost_out = ctypes.c_float(0.0)
    iters_out = ctypes.c_int(0)
    converged_out = ctypes.c_int(0)

    rc = lib.solve_mpc_step(
        x_arr,
        u_prev_arr,
        w_arr,
        u_out_arr,
        ctypes.byref(cost_out),
        ctypes.byref(iters_out),
        ctypes.byref(converged_out),
    )
    if rc != 0:
        raise RuntimeError(f"solve_mpc_step failed with rc={rc}")

    return {
        "u": [float(u_out_arr[0]), float(u_out_arr[1])],
        "cost": float(cost_out.value),
        "iterations": int(iters_out.value),
        "converged": int(converged_out.value),
    }


def build_acc_qp_payload_legacy_host(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    """Build the reduced ACC QP payload using the C legacy host formulation."""
    lib = _load_lib()

    x_arr = (ctypes.c_float * 3)(float(x[0]), float(x[1]), float(x[2]))
    u_prev_arr = (ctypes.c_float * 2)(float(u_prev[0]), float(u_prev[1]))
    w_arr = (ctypes.c_float * 2)(float(w[0]), float(w[1]))

    p_arr = (ctypes.c_float * 4)(0.0, 0.0, 0.0, 0.0)
    q_arr = (ctypes.c_float * 2)(0.0, 0.0)
    l_arr = (ctypes.c_float * 2)(0.0, 0.0)
    u_arr = (ctypes.c_float * 2)(0.0, 0.0)

    rc = lib.build_acc_qp_matrices(
        x_arr,
        u_prev_arr,
        w_arr,
        p_arr,
        q_arr,
        l_arr,
        u_arr,
    )
    if rc != 0:
        raise RuntimeError(f"build_acc_qp_matrices failed with rc={rc}")

    p00 = float(p_arr[0])
    p01 = float(p_arr[1])
    p11 = float(p_arr[3])

    return {
        "n": 2,
        "m": 2,
        "P_colptr": [0, 1, 3],
        "P_rowind": [0, 0, 1],
        "P_data": [p00, p01, p11],
        "q": [float(q_arr[0]), float(q_arr[1])],
        "A_colptr": [0, 1, 2],
        "A_rowind": [0, 1],
        "A_data": [1.0, 1.0],
        "l": [float(l_arr[0]), float(l_arr[1])],
        "u": [float(u_arr[0]), float(u_arr[1])],
    }
