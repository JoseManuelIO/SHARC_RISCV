#!/usr/bin/env python3
"""Host MPC boundary API (C ABI first, legacy-python fallback).

This module is the stable boundary for host-side MPC/QP services.
It exposes plain Python primitives and hides backend-specific details.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Callable


HOST_API_VERSION = "1.0"
DEFAULT_BACKEND = os.getenv("SHARC_HOST_API_BACKEND", "c_abi").strip().lower() or "c_abi"
ENABLE_FALLBACK = os.getenv("SHARC_HOST_API_FALLBACK", "1").strip().lower() not in {"0", "false", "no", "off"}
OFFICIAL_RISCV_MODE = os.getenv("SHARC_OFFICIAL_RISCV_MODE", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_wrapper_builder_cache: Callable[[list[float], list[float], list[float]], dict] | None = None


def _load_wrapper_builder() -> Callable[[list[float], list[float], list[float]], dict]:
    global _wrapper_builder_cache
    if _wrapper_builder_cache is not None:
        return _wrapper_builder_cache

    wrapper_path = Path(__file__).resolve().parents[1] / "sharc_patches" / "acc_example" / "gvsoc_controller_wrapper_v2.py"
    spec = importlib.util.spec_from_file_location("_sharc_wrapper_qp_builder", wrapper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load wrapper module from {wrapper_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    builder = getattr(mod, "build_acc_qp_payload", None)
    if builder is None:
        raise RuntimeError("wrapper module does not expose build_acc_qp_payload")
    _wrapper_builder_cache = builder
    return builder


def _solve_c_abi(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    from mpc_legacy_host_solver import solve_acc_step_legacy_host  # noqa: WPS433

    return solve_acc_step_legacy_host(x, u_prev, w)


def _solve_python(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    from mpc_legacy_python import solve_acc_step_legacy_python  # noqa: WPS433

    return solve_acc_step_legacy_python(x, u_prev, w)


def _build_payload_c_abi(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    from mpc_legacy_host_solver import build_acc_qp_payload_legacy_host  # noqa: WPS433

    return build_acc_qp_payload_legacy_host(x, u_prev, w)


def _build_payload_wrapper(x: list[float], u_prev: list[float], w: list[float]) -> dict:
    builder = _load_wrapper_builder()
    # Wrapper builder expects signature: (x, w, u_prev)
    return builder(x, w, u_prev)


def _backend_order(preferred: str, allow_fallback: bool, fallback_backend: str) -> list[str]:
    preferred = preferred.strip().lower()
    fallback_backend = fallback_backend.strip().lower()
    if preferred not in {"c_abi", "python", "wrapper"}:
        preferred = "c_abi"
    if fallback_backend not in {"c_abi", "python", "wrapper"}:
        fallback_backend = "python"
    if not allow_fallback or preferred == fallback_backend:
        return [preferred]
    return [preferred, fallback_backend]


def _assert_host_solver_allowed() -> None:
    if OFFICIAL_RISCV_MODE:
        raise RuntimeError("host solver API disabled in SHARC_OFFICIAL_RISCV_MODE")


def solve_acc_step_host(
    x: list[float],
    u_prev: list[float],
    w: list[float],
    *,
    backend: str = DEFAULT_BACKEND,
    allow_fallback: bool = ENABLE_FALLBACK,
    fallback_backend: str = "python",
) -> dict:
    """Solve one host MPC step through the boundary API."""
    _assert_host_solver_allowed()
    errors: list[str] = []
    for candidate in _backend_order(backend, allow_fallback, fallback_backend):
        try:
            if candidate == "c_abi":
                out = _solve_c_abi(x, u_prev, w)
            elif candidate == "python":
                out = _solve_python(x, u_prev, w)
            else:
                raise RuntimeError(f"unsupported solve backend: {candidate}")
            result = dict(out)
            result["backend"] = candidate
            return result
        except Exception as exc:  # pragma: no cover - fallback path
            errors.append(f"{candidate}: {exc}")
            continue
    raise RuntimeError("all solve backends failed: " + " | ".join(errors))


def build_acc_qp_payload_host(
    x: list[float],
    u_prev: list[float],
    w: list[float],
    *,
    backend: str = DEFAULT_BACKEND,
    allow_fallback: bool = ENABLE_FALLBACK,
    fallback_backend: str = "wrapper",
) -> tuple[dict, str]:
    """Build reduced ACC QP payload through the boundary API.

    In official mode, host-side QP formulation is allowed (dynamics/formulation on host,
    solve on RISC-V). Only host-side solve is blocked.
    """
    errors: list[str] = []
    for candidate in _backend_order(backend, allow_fallback, fallback_backend):
        try:
            if candidate == "c_abi":
                payload = _build_payload_c_abi(x, u_prev, w)
            elif candidate == "wrapper":
                payload = _build_payload_wrapper(x, u_prev, w)
            else:
                raise RuntimeError(f"unsupported payload backend: {candidate}")
            return payload, candidate
        except Exception as exc:  # pragma: no cover - fallback path
            errors.append(f"{candidate}: {exc}")
            continue
    raise RuntimeError("all payload backends failed: " + " | ".join(errors))
