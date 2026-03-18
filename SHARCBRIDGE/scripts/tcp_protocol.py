#!/usr/bin/env python3
"""
TCP protocol validation helpers for SHARCBRIDGE.

T1 scope:
- define a strict request/response contract for socket transport
- keep legacy compatibility for current compute_mpc messages
"""

from __future__ import annotations

from typing import Any


class ValidationResult:
    """Minimal immutable-like result object compatible with dynamic imports in tests."""

    __slots__ = ("ok", "error")

    def __init__(self, ok: bool, error: str = "") -> None:
        self.ok = ok
        self.error = error


_ALLOWED_TYPES = {"compute_mpc", "kernel_op", "shutdown", "init", "step", "heartbeat", "qp_solve"}
_ALLOWED_KERNEL_OPS = {"matvec_dense", "matvec_sparse", "dot", "axpy", "box_project"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_number_list(value: Any, expected_len: int | None = None) -> bool:
    if not isinstance(value, list):
        return False
    if expected_len is not None and len(value) != expected_len:
        return False
    return all(_is_number(v) for v in value)


def validate_request(payload: Any, require_request_id: bool = False) -> ValidationResult:
    """
    Validate incoming TCP request payload.

    By default, request_id is optional to keep backward compatibility with
    existing compute_mpc clients. New transport flows should set it.
    """
    if not isinstance(payload, dict):
        return ValidationResult(False, "payload must be an object")

    req_type = payload.get("type")
    if isinstance(req_type, str):
        req_type = req_type.lower()
        payload["type"] = req_type
    if req_type not in _ALLOWED_TYPES:
        return ValidationResult(
            False,
            "type is required and must be one of compute_mpc/kernel_op/shutdown/init/step/heartbeat/qp_solve",
        )

    if require_request_id and "request_id" not in payload:
        return ValidationResult(False, "request_id is required")

    if "request_id" in payload and not isinstance(payload["request_id"], (str, int)):
        return ValidationResult(False, "request_id must be str or int")

    if req_type == "shutdown":
        return ValidationResult(True, "")

    if req_type in {"heartbeat", "init"}:
        if "session_id" in payload and not isinstance(payload["session_id"], (str, int)):
            return ValidationResult(False, "session_id must be str or int")
        if req_type == "init" and "persistent_workers" in payload:
            workers = payload["persistent_workers"]
            if not isinstance(workers, int) or workers <= 0:
                return ValidationResult(False, "persistent_workers must be int > 0")
        return ValidationResult(True, "")

    if req_type in {"compute_mpc", "step"}:
        if "k" in payload and not isinstance(payload["k"], int):
            return ValidationResult(False, "k must be int")
        if "t" in payload and not _is_number(payload["t"]):
            return ValidationResult(False, "t must be numeric")
        if "x" in payload and not _is_number_list(payload["x"], expected_len=3):
            return ValidationResult(False, "x must be [3 numbers]")
        if "w" in payload and not _is_number_list(payload["w"], expected_len=2):
            return ValidationResult(False, "w must be [2 numbers]")
        if "u_prev" in payload and not _is_number_list(payload["u_prev"], expected_len=2):
            return ValidationResult(False, "u_prev must be [2 numbers]")
        return ValidationResult(True, "")

    if req_type == "qp_solve":
        has_payload = isinstance(payload.get("qp_payload"), dict)
        has_blob_hex = isinstance(payload.get("qp_blob_hex"), str) and len(payload.get("qp_blob_hex", "")) > 0
        has_host_vectors = (
            _is_number_list(payload.get("x"), expected_len=3)
            and _is_number_list(payload.get("w"), expected_len=2)
        )
        if not has_payload and not has_blob_hex and not has_host_vectors:
            return ValidationResult(False, "qp_solve requires qp_payload object, qp_blob_hex string, or x/w vectors")
        if "u_prev" in payload and not _is_number_list(payload["u_prev"], expected_len=2):
            return ValidationResult(False, "u_prev must be [2 numbers]")
        settings = payload.get("settings")
        if settings is not None:
            if not isinstance(settings, dict):
                return ValidationResult(False, "settings must be object")
            if "max_iter" in settings and (not isinstance(settings["max_iter"], int) or settings["max_iter"] <= 0):
                return ValidationResult(False, "settings.max_iter must be int > 0")
            if "tol" in settings and not _is_number(settings["tol"]):
                return ValidationResult(False, "settings.tol must be numeric")
            if "rho" in settings and not _is_number(settings["rho"]):
                return ValidationResult(False, "settings.rho must be numeric")
        return ValidationResult(True, "")

    # req_type == kernel_op
    op = payload.get("op")
    if op not in _ALLOWED_KERNEL_OPS:
        return ValidationResult(False, f"op must be one of {sorted(_ALLOWED_KERNEL_OPS)}")
    if "payload" not in payload or not isinstance(payload["payload"], dict):
        return ValidationResult(False, "kernel_op must include object payload")
    return ValidationResult(True, "")


def validate_response(payload: Any) -> ValidationResult:
    """Validate server response payload contract."""
    if not isinstance(payload, dict):
        return ValidationResult(False, "response must be an object")

    if "status" not in payload:
        return ValidationResult(False, "response must include status")
    if not isinstance(payload["status"], str):
        return ValidationResult(False, "status must be str")

    if "request_id" in payload and not isinstance(payload["request_id"], (str, int)):
        return ValidationResult(False, "request_id must be str or int")

    # If a compute-style response includes u, ensure shape.
    if "u" in payload and not _is_number_list(payload["u"], expected_len=2):
        return ValidationResult(False, "u must be [2 numbers]")
    if "x" in payload and not _is_number_list(payload["x"]):
        return ValidationResult(False, "x must be numeric list")

    for key in ("cost", "t_delay"):
        if key in payload and not _is_number(payload[key]):
            return ValidationResult(False, f"{key} must be numeric")

    for key in ("k", "iterations", "cycles"):
        if key in payload and not isinstance(payload[key], int):
            return ValidationResult(False, f"{key} must be int")

    return ValidationResult(True, "")


def build_error_response(message: str, request_id: str | int | None = None, code: str = "BAD_REQUEST") -> dict:
    """Build canonical error response payload."""
    response = {
        "status": "ERROR",
        "error_code": code,
        "error": message,
    }
    if request_id is not None:
        response["request_id"] = request_id
    return response
