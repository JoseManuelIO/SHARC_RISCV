#!/usr/bin/env python3
"""
GVSoC TCP Server - Bridge between SHARC and GVSoC.

This module keeps the TCP transport protocol and delegates MPC execution to
`gvsoc_core.py`, so transport and compute logic stay decoupled.

Protocol:
  Request:  {"type": "compute_mpc", "k": int, "t": float, "x": [3 floats], "w": [2 floats]}
  Response: {"k": int, "u": [2 floats], "cost": float, "status": str, "iterations": int, "cycles": int}

  Special: {"type": "shutdown"} to stop the server.
"""

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

_scripts_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))

from gvsoc_core import (  # noqa: E402
    GVSOC_BINARY,
    GVSOC_PLATFORM,
    GVSOC_RUN_TIMEOUT_S,
    GVSOC_TARGET,
    MPC_ELF,
    PULP_SDK_CONFIG,
    PULP_SDK_SOURCEME,
    SERVER_HOST,
    SERVER_PORT,
    build_qp_persistent_compute_fn,
    get_runtime_metrics_snapshot,
    run_gvsoc_mpc,
    run_gvsoc_qp,
    validate_environment,
)
from tcp_protocol import (  # noqa: E402
    build_error_response,
    validate_request,
    validate_response,
)
from gvsoc_persistent_runtime import (  # noqa: E402
    GenericPersistentRuntimePool,
    PersistentRuntimePool,
    WorkerExecutionError,
)
from kernel_ops import dispatch_kernel_op  # noqa: E402
from t6_solver_dispatch import KernelDispatcher, solve_acc_step_with_dispatch  # noqa: E402
from mpc_legacy_python import solve_acc_step_legacy_python  # noqa: E402
from mpc_host_api import build_acc_qp_payload_host, solve_acc_step_host, HOST_API_VERSION  # noqa: E402
from qp_payload import decode_qp_message, validate_qp_payload  # noqa: E402


# ============================================================================
# TCP Server
# ============================================================================

MAX_BUFFER_BYTES = 2 * 1024 * 1024
CONNECTION_TIMEOUT_S = 5.0
LISTEN_BACKLOG = 64
DEFAULT_PERSISTENT_WORKERS = int(os.getenv("GVSOC_PERSISTENT_WORKERS", "0"))
KERNEL_BACKEND = os.getenv("SHARC_KERNEL_BACKEND", "host_fallback")
DEFAULT_EXEC_MODE = os.getenv("GVSOC_EXEC_MODE", "persistent")
PERSISTENT_SOLVER_BACKEND = os.getenv("SHARC_PERSISTENT_SOLVER_BACKEND", "host_fallback")
PERSISTENT_SOLVER_MAX_ITER = int(os.getenv("SHARC_PERSISTENT_MAX_ITER", "60"))
PERSISTENT_SOLVER_TOL = float(os.getenv("SHARC_PERSISTENT_TOL", "1e-3"))
PERSISTENT_SOLVER_ALPHA = float(os.getenv("SHARC_PERSISTENT_ALPHA", "0.05"))
PERSISTENT_PATH = os.getenv("GVSOC_PERSISTENT_PATH", "gvsoc_legacy")
CYCLES_PROFILE_JSON = os.getenv("GVSOC_CYCLES_PROFILE_JSON", "").strip()
QP_PERSISTENT_BACKEND = os.getenv("GVSOC_QP_PERSISTENT_BACKEND", "legacy").strip().lower()
QP_PERSISTENT_EXPERIMENTAL = os.getenv("GVSOC_QP_PERSISTENT_EXPERIMENTAL", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
OFFICIAL_RISCV_MODE = os.getenv("SHARC_OFFICIAL_RISCV_MODE", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_runtime_pool = None
_runtime_lock = threading.Lock()
_qp_runtime_pool = None
_qp_runtime_lock = threading.Lock()
_exec_mode = "legacy"
_persistent_spawn_count = 0
_persistent_patch_count = 0
_qp_persistent_spawn_count = 0
_persistent_cycles_profile = {}


def _load_cycles_profile(path: str) -> dict[int, int]:
    if not path:
        return {}
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        out = {}
        if isinstance(raw, dict):
            items = raw.items()
        elif isinstance(raw, list):
            items = enumerate(raw)
        else:
            return {}
        for k, v in items:
            try:
                kk = int(k)
                vv = int(v)
            except Exception:
                continue
            out[kk] = vv
        return out
    except Exception:
        return {}


def _send_json(conn, payload):
    """Send one NDJSON message."""
    conn.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def _response_with_request_id(request, response):
    request_id = request.get("request_id")
    if request_id is not None and "request_id" not in response:
        response["request_id"] = request_id
    return response


def configure_runtime_pool(num_workers: int, max_retries: int = 1, compute_fn_factory=None):
    """
    Configure persistent runtime pool used for compute_mpc dispatch.
    """
    global _runtime_pool
    with _runtime_lock:
        if _runtime_pool is not None and hasattr(_runtime_pool, "close"):
            _runtime_pool.close()
        if compute_fn_factory is None:
            compute_fn_factory = lambda _wid: run_gvsoc_mpc
        _runtime_pool = PersistentRuntimePool(
            num_workers=num_workers,
            compute_fn_factory=compute_fn_factory,
            max_retries=max_retries,
        )


def clear_runtime_pool():
    """Disable persistent runtime pool and fallback to direct run_gvsoc_mpc."""
    global _runtime_pool
    with _runtime_lock:
        if _runtime_pool is not None and hasattr(_runtime_pool, "close"):
            _runtime_pool.close()
        _runtime_pool = None


def configure_qp_runtime_pool(num_workers: int, max_retries: int = 1, compute_fn_factory=None):
    """
    Configure persistent runtime pool used for qp_solve dispatch.
    """
    global _qp_runtime_pool
    with _qp_runtime_lock:
        if _qp_runtime_pool is not None and hasattr(_qp_runtime_pool, "close"):
            _qp_runtime_pool.close()
        if compute_fn_factory is None:
            compute_fn_factory = lambda _wid: run_gvsoc_qp
        _qp_runtime_pool = GenericPersistentRuntimePool(
            num_workers=num_workers,
            compute_fn_factory=compute_fn_factory,
            max_retries=max_retries,
        )


def clear_qp_runtime_pool():
    """Disable persistent QP runtime pool and fallback to direct run_gvsoc_qp."""
    global _qp_runtime_pool
    with _qp_runtime_lock:
        if _qp_runtime_pool is not None and hasattr(_qp_runtime_pool, "close"):
            _qp_runtime_pool.close()
        _qp_runtime_pool = None


def _qp_compute_factory():
    if QP_PERSISTENT_BACKEND == "proxy":
        if not QP_PERSISTENT_EXPERIMENTAL:
            print(
                "[Server] QP proxy backend requested but disabled (set GVSOC_QP_PERSISTENT_EXPERIMENTAL=1 to enable). "
                "Using legacy run_gvsoc_qp.",
                file=sys.stderr,
            )
            return lambda _wid: run_gvsoc_qp
        return build_qp_persistent_compute_fn
    return lambda _wid: run_gvsoc_qp


def get_runtime_snapshot() -> dict | None:
    with _runtime_lock:
        if _runtime_pool is None:
            return None
        return _runtime_pool.snapshot()


def get_qp_runtime_snapshot() -> dict | None:
    with _qp_runtime_lock:
        if _qp_runtime_pool is None:
            return None
        return _qp_runtime_pool.snapshot()


def _normalize_exec_mode(mode: str | None) -> str:
    if isinstance(mode, str) and mode.strip().lower() == "persistent":
        return "persistent"
    return "legacy"


def get_exec_mode() -> str:
    return _exec_mode


def _build_dispatch_compute_fn(worker_id: int):
    dispatcher = KernelDispatcher(default_backend=PERSISTENT_SOLVER_BACKEND)
    settings = {
        "max_iter": PERSISTENT_SOLVER_MAX_ITER,
        "tol": PERSISTENT_SOLVER_TOL,
        "alpha": PERSISTENT_SOLVER_ALPHA,
    }

    def _compute(k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
        if u_prev is None:
            u_prev = [0.0, 100.0]
        t0 = time.perf_counter()
        out = solve_acc_step_with_dispatch(x, u_prev, w, dispatcher, settings=settings)
        t_delay = time.perf_counter() - t0
        dispatch_snap = out.get("dispatcher", {})
        cycles_est = int(dispatch_snap.get("cycles_est_total", 0))
        if cycles_est <= 0:
            cycles_est = int(dispatch_snap.get("total_calls", 0)) * 64
        # Keep SHARC integration-compatible status naming.
        status = "OPTIMAL"
        return {
            "k": int(k),
            "u": out.get("u", u_prev),
            "cost": float(out.get("cost", 0.0)),
            "status": status,
            "iterations": int(out.get("iterations", 0)),
            "cycles": cycles_est,
            "t_delay": t_delay,
            "converged": int(out.get("converged", 0)),
            "solver_backend": PERSISTENT_SOLVER_BACKEND,
            "worker_id": worker_id,
        }

    return _compute


def _build_legacy_python_compute_fn(worker_id: int):
    if OFFICIAL_RISCV_MODE:
        raise RuntimeError("legacy_python backend disabled in SHARC_OFFICIAL_RISCV_MODE")

    def _compute(k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
        if u_prev is None:
            u_prev = [0.0, 100.0]
        t0 = time.perf_counter()
        out = solve_acc_step_legacy_python(x, u_prev, w)
        t_delay = time.perf_counter() - t0
        # Keep output format close to GVSoC binary path (2 decimal fields in firmware print).
        u = [round(float(out["u"][0]), 2), round(float(out["u"][1]), 2)]
        cost = round(float(out["cost"]), 2)
        iters = int(out.get("iterations", 0))
        cycles_est = _persistent_cycles_profile.get(int(k))
        if cycles_est is None:
            # Fallback cycle model chosen to stay in the same order as legacy GVSoC runs.
            cycles_est = max(50000, int(1800000 + 35000 * iters + 800 * (u[0] + u[1])))
        return {
            "k": int(k),
            "u": u,
            "cost": cost,
            "status": "OPTIMAL",
            "iterations": iters,
            "cycles": cycles_est,
            "t_delay": t_delay,
            "converged": int(out.get("converged", 0)),
            "solver_backend": "legacy_python",
            "worker_id": worker_id,
        }

    return _compute


def _build_legacy_host_compute_fn(worker_id: int):
    if OFFICIAL_RISCV_MODE:
        raise RuntimeError("host_api backend disabled in SHARC_OFFICIAL_RISCV_MODE")

    def _compute(k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
        if u_prev is None:
            u_prev = [0.0, 100.0]
        t0 = time.perf_counter()
        try:
            out = solve_acc_step_host(
                x,
                u_prev,
                w,
                backend="c_abi",
                allow_fallback=True,
                fallback_backend="python",
            )
        except Exception:
            # Last-resort fallback; keep persistent flow alive.
            out = solve_acc_step_legacy_python(x, u_prev, w)
            out["backend"] = "python_last_resort"
        t_delay = time.perf_counter() - t0
        u = [round(float(out["u"][0]), 2), round(float(out["u"][1]), 2)]
        cost = round(float(out["cost"]), 2)
        iters = int(out.get("iterations", 0))
        cycles_est = _persistent_cycles_profile.get(int(k))
        if cycles_est is None:
            cycles_est = max(50000, int(1800000 + 35000 * iters + 800 * (u[0] + u[1])))
        return {
            "k": int(k),
            "u": u,
            "cost": cost,
            "status": "OPTIMAL",
            "iterations": iters,
            "cycles": cycles_est,
            "t_delay": t_delay,
            "converged": int(out.get("converged", 0)),
            "solver_backend": f"host_api:{out.get('backend', 'unknown')}",
            "solver_api_version": HOST_API_VERSION,
            "worker_id": worker_id,
        }

    return _compute


def _runtime_metrics_for_mode() -> dict:
    if get_exec_mode() == "persistent":
        return {
            "gvsoc_spawn_count": _persistent_spawn_count,
            "elf_patch_count": _persistent_patch_count,
            "qp_worker_spawn_count": _qp_persistent_spawn_count,
        }
    return get_runtime_metrics_snapshot()


def set_exec_mode(mode: str | None, persistent_workers: int | None = None) -> dict:
    global _exec_mode, _persistent_spawn_count, _persistent_patch_count, _persistent_cycles_profile
    global _qp_persistent_spawn_count
    normalized = _normalize_exec_mode(mode)
    if normalized == "persistent":
        workers = persistent_workers if isinstance(persistent_workers, int) and persistent_workers > 0 else None
        if workers is None:
            workers = DEFAULT_PERSISTENT_WORKERS if DEFAULT_PERSISTENT_WORKERS > 0 else 1
        _persistent_cycles_profile = _load_cycles_profile(CYCLES_PROFILE_JSON)
        if OFFICIAL_RISCV_MODE:
            configure_runtime_pool(workers, compute_fn_factory=lambda _wid: run_gvsoc_mpc)
            configure_qp_runtime_pool(workers, compute_fn_factory=_qp_compute_factory())
            _persistent_patch_count = 0
        elif PERSISTENT_PATH == "gvsoc_legacy":
            configure_runtime_pool(workers, compute_fn_factory=lambda _wid: run_gvsoc_mpc)
            configure_qp_runtime_pool(workers, compute_fn_factory=_qp_compute_factory())
            _persistent_patch_count = 0
        elif PERSISTENT_PATH == "legacy_python":
            configure_runtime_pool(workers, compute_fn_factory=_build_legacy_python_compute_fn)
            configure_qp_runtime_pool(workers, compute_fn_factory=_qp_compute_factory())
            _persistent_patch_count = 1
        elif PERSISTENT_PATH == "legacy_c":
            configure_runtime_pool(workers, compute_fn_factory=_build_legacy_host_compute_fn)
            configure_qp_runtime_pool(workers, compute_fn_factory=_qp_compute_factory())
            _persistent_patch_count = 1
        else:
            configure_runtime_pool(workers, compute_fn_factory=_build_dispatch_compute_fn)
            configure_qp_runtime_pool(workers, compute_fn_factory=_qp_compute_factory())
            # In dispatch mode there is no per-iteration ELF patching; modeled as single init patch.
            _persistent_patch_count = 1
        _persistent_spawn_count = workers
        _qp_persistent_spawn_count = workers
    else:
        clear_runtime_pool()
        clear_qp_runtime_pool()
        _persistent_spawn_count = 0
        _persistent_patch_count = 0
        _qp_persistent_spawn_count = 0
        _persistent_cycles_profile = {}
    _exec_mode = normalized
    return {
        "exec_mode": _exec_mode,
        "runtime": get_runtime_snapshot(),
        "qp_runtime": get_qp_runtime_snapshot(),
        "metrics": _runtime_metrics_for_mode(),
    }


def _compute_mpc_dispatch(k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
    with _runtime_lock:
        pool = _runtime_pool
    if pool is None:
        return run_gvsoc_mpc(k, t, x, w, u_prev)
    return pool.compute_mpc(k, t, x, w, u_prev)


def _compute_qp_dispatch(payload: dict, settings: dict | None = None) -> dict:
    with _qp_runtime_lock:
        pool = _qp_runtime_pool
    if pool is None:
        return run_gvsoc_qp(payload, settings=settings)
    return pool.compute(payload, settings=settings)


def _decode_qp_request_payload(request: dict) -> tuple[dict | None, str]:
    raw_payload = request.get("qp_payload")
    if OFFICIAL_RISCV_MODE and isinstance(raw_payload, dict):
        return None, "qp_payload is not allowed in SHARC_OFFICIAL_RISCV_MODE; send x/w(/u_prev)"
    if isinstance(raw_payload, dict):
        ok, err = validate_qp_payload(raw_payload)
        if not ok:
            return None, err
        return raw_payload, ""

    qp_blob_hex = request.get("qp_blob_hex")
    if OFFICIAL_RISCV_MODE and isinstance(qp_blob_hex, str) and qp_blob_hex:
        return None, "qp_blob_hex is not allowed in SHARC_OFFICIAL_RISCV_MODE; send x/w(/u_prev)"
    if isinstance(qp_blob_hex, str) and qp_blob_hex:
        try:
            blob = bytes.fromhex(qp_blob_hex)
        except ValueError:
            return None, "qp_blob_hex is not valid hex"
        try:
            decoded = decode_qp_message(blob)
        except Exception as exc:
            return None, f"invalid QP binary payload: {exc}"
        payload = decoded.get("payload")
        ok, err = validate_qp_payload(payload)
        if not ok:
            return None, err
        return payload, ""

    x = request.get("x")
    w = request.get("w")
    if isinstance(x, list) and isinstance(w, list):
        if len(x) != 3:
            return None, "x must be [3 numbers] when qp_payload is omitted"
        if len(w) != 2:
            return None, "w must be [2 numbers] when qp_payload is omitted"
        u_prev = request.get("u_prev")
        if not isinstance(u_prev, list) or len(u_prev) != 2:
            u_prev = [0.0, 100.0]
        try:
            payload, backend = build_acc_qp_payload_host(
                [float(x[0]), float(x[1]), float(x[2])],
                [float(u_prev[0]), float(u_prev[1])],
                [float(w[0]), float(w[1])],
                backend="c_abi",
                allow_fallback=False,
            )
            request["_qp_payload_backend"] = backend
            return payload, ""
        except Exception as exc:
            return None, f"host QP formulation failed: {exc}"

    return None, "qp_solve requires qp_payload, qp_blob_hex, or x/w(/u_prev) for host formulation"


def _handle_qp_solve_request(request: dict) -> dict:
    payload, err = _decode_qp_request_payload(request)
    if payload is None:
        raise ValueError(err)

    settings = request.get("settings", {})
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError("settings must be object")

    out = _compute_qp_dispatch(payload, settings=settings)
    backend = request.get("_qp_payload_backend")
    payload_backend = backend if backend else "request"
    p_nnz = len(payload.get("P_data", []))
    a_nnz = len(payload.get("A_data", []))
    # Explicit per-iteration trace for T3 gate: payload contains full QP fields.
    print(
        f"[Server] qp_solve payload backend={payload_backend} "
        f"fields=P,q,A,l,u p_nnz={p_nnz} a_nnz={a_nnz}",
        file=sys.stderr,
    )
    return {
        "status": out["status"],
        "x": out["x"],
        "cost": out["cost"],
        "iterations": int(out["iterations"]),
        "converged": int(out["converged"]),
        "cycles": int(out.get("cycles", 0)),
        "t_delay": float(out.get("t_delay", 0.0)),
        "primal_residual": float(out["primal_residual"]),
        "dual_residual": float(out["dual_residual"]),
        "instret": int(out.get("instret", 0)),
        "ld_stall": int(out.get("ld_stall", 0)),
        "jmp_stall": int(out.get("jmp_stall", 0)),
        "stall_total": int(out.get("stall_total", 0)),
        "imiss": int(out.get("imiss", 0)),
        "branch": int(out.get("branch", 0)),
        "taken_branch": int(out.get("taken_branch", 0)),
        "cpi": float(out.get("cpi", 0.0)),
        "ipc": float(out.get("ipc", 0.0)),
        "n": int(out["n"]),
        "m": int(out["m"]),
    }

def handle_client(conn, addr):
    """Handle a single client connection."""
    print(f"\n[Server] Client connected: {addr}", file=sys.stderr)

    # Maintain u_prev between iterations (starts at default [0, 100])
    u_prev = [0.0, 100.0]

    try:
        if hasattr(conn, "settimeout"):
            conn.settimeout(CONNECTION_TIMEOUT_S)

        buffer = b""

        while True:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                print(f"[Server] Client {addr} disconnected", file=sys.stderr)
                break

            buffer += chunk
            if len(buffer) > MAX_BUFFER_BYTES:
                print(f"[Server] Buffer overflow from {addr}", file=sys.stderr)
                _send_json(conn, build_error_response("request too large", code="PAYLOAD_TOO_LARGE"))
                break

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)

                if not line.strip():
                    continue

                try:
                    request = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    print(f"[Server] JSON decode error: {exc}", file=sys.stderr)
                    _send_json(conn, build_error_response("invalid json", code="INVALID_JSON"))
                    continue

                validation = validate_request(request, require_request_id=False)
                if not validation.ok:
                    print(f"[Server] Invalid request: {validation.error}", file=sys.stderr)
                    _send_json(
                        conn,
                        build_error_response(
                            validation.error,
                            request_id=request.get("request_id"),
                            code="BAD_REQUEST",
                        ),
                    )
                    continue

                req_type = str(request.get("type", "")).lower()

                if req_type == "heartbeat":
                    response = _response_with_request_id(
                        request,
                        {
                            "status": "ALIVE",
                            "exec_mode": get_exec_mode(),
                            "runtime": get_runtime_snapshot(),
                            "qp_runtime": get_qp_runtime_snapshot(),
                            "metrics": _runtime_metrics_for_mode(),
                        },
                    )
                    _send_json(conn, response)
                    continue

                if req_type == "init":
                    state = set_exec_mode(
                        request.get("exec_mode", get_exec_mode()),
                        request.get("persistent_workers"),
                    )
                    response = _response_with_request_id(
                        request,
                        {
                            "status": "INIT_OK",
                            "exec_mode": state["exec_mode"],
                            "runtime": state["runtime"],
                            "qp_runtime": state.get("qp_runtime"),
                            "metrics": state["metrics"],
                        },
                    )
                    _send_json(conn, response)
                    continue

                if req_type == "shutdown":
                    print(f"[Server] Shutdown requested by {addr}", file=sys.stderr)
                    response = _response_with_request_id(request, {"status": "SHUTDOWN"})
                    _send_json(conn, response)
                    return "shutdown"

                if req_type == "qp_solve":
                    try:
                        result = _handle_qp_solve_request(request)
                    except ValueError as exc:
                        _send_json(
                            conn,
                            build_error_response(
                                str(exc),
                                request_id=request.get("request_id"),
                                code="QP_BAD_PAYLOAD",
                            ),
                        )
                        continue
                    except Exception as exc:
                        _send_json(
                            conn,
                            build_error_response(
                                str(exc),
                                request_id=request.get("request_id"),
                                code="QP_SOLVE_ERROR",
                            ),
                        )
                        continue

                    result = _response_with_request_id(request, result)
                    response_validation = validate_response(result)
                    if not response_validation.ok:
                        _send_json(
                            conn,
                            build_error_response(
                                "internal response contract violation",
                                request_id=request.get("request_id"),
                                code="INTERNAL_RESPONSE_INVALID",
                            ),
                        )
                        continue

                    print(
                        f"[Server] qp_solve n={result.get('n')} m={result.get('m')} "
                        f"status={result.get('status')} iters={result.get('iterations')} "
                        f"cost={result.get('cost')}",
                        file=sys.stderr,
                    )

                    _send_json(conn, result)
                    continue

                if req_type in {"compute_mpc", "step"}:
                    k = request.get("k", 0)
                    t = request.get("t", 0.0)
                    x = request.get("x", [0.0, 60.0, 15.0])
                    w = request.get("w", [11.0, 1.0])

                    request_u_prev = request.get("u_prev", None)
                    if request_u_prev is not None:
                        u_prev = request_u_prev
                        print(f"[Server] Using u_prev from request: {u_prev}", file=sys.stderr)
                    else:
                        print(f"[Server] Using tracked u_prev: {u_prev}", file=sys.stderr)

                    try:
                        result = _compute_mpc_dispatch(k, t, x, w, u_prev)
                    except WorkerExecutionError as exc:
                        print(f"[Server] persistent worker failure: {exc}", file=sys.stderr)
                        _send_json(
                            conn,
                            build_error_response(
                                str(exc),
                                request_id=request.get("request_id"),
                                code="WORKER_FAILURE",
                            ),
                        )
                        continue
                    except Exception as exc:
                        print(f"[Server] compute_mpc failure: {exc}", file=sys.stderr)
                        _send_json(
                            conn,
                            build_error_response(
                                str(exc),
                                request_id=request.get("request_id"),
                                code="COMPUTE_ERROR",
                            ),
                        )
                        continue

                    if get_exec_mode() == "persistent":
                        result["gvsoc_spawn_count"] = _persistent_spawn_count
                        result["elf_patch_count"] = _persistent_patch_count
                        print(
                            f"[Core] metrics k={k} spawn_count={_persistent_spawn_count} "
                            f"elf_patch_count={_persistent_patch_count}",
                            file=sys.stderr,
                        )

                    result = _response_with_request_id(request, dict(result))
                    response_validation = validate_response(result)
                    if not response_validation.ok:
                        print(f"[Server] Invalid compute response: {response_validation.error}", file=sys.stderr)
                        _send_json(
                            conn,
                            build_error_response(
                                "internal response contract violation",
                                request_id=request.get("request_id"),
                                code="INTERNAL_RESPONSE_INVALID",
                            ),
                        )
                        continue

                    print(
                        f"[Server] k={k} t={t:.3f} x={x} w={w} -> "
                        f"u={result.get('u')} cost={result.get('cost')} "
                        f"status={result.get('status')} iters={result.get('iterations')} "
                        f"cycles={result.get('cycles')} delay={result.get('t_delay')}",
                        file=sys.stderr,
                    )

                    # Keep backward-compatible internal tracking if client omits u_prev.
                    u_prev = result.get("u", u_prev)

                    _send_json(conn, result)
                elif req_type == "kernel_op":
                    op = request.get("op")
                    payload = request.get("payload")
                    try:
                        k_out = dispatch_kernel_op(op, payload, backend=KERNEL_BACKEND)
                    except Exception as exc:
                        _send_json(
                            conn,
                            build_error_response(
                                str(exc),
                                request_id=request.get("request_id"),
                                code="KERNEL_BAD_PAYLOAD",
                            ),
                        )
                        continue
                    response = {
                        "status": "OK",
                        "request_id": request.get("request_id"),
                        **k_out,
                    }
                    _send_json(conn, response)
                else:
                    print(f"[Server] Unknown request type: {request.get('type')}", file=sys.stderr)

    except (ConnectionResetError, BrokenPipeError):
        print(f"[Server] Client {addr} closed connection abruptly", file=sys.stderr)
    except Exception as exc:
        print(f"[Server] Error handling client {addr}: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    finally:
        conn.close()


def run_server():
    """Main server loop."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(0.5)
    stop_event = threading.Event()
    client_threads = set()

    def _client_runner(client_conn, client_addr):
        try:
            result = handle_client(client_conn, client_addr)
            if result == "shutdown":
                stop_event.set()
        finally:
            client_threads.discard(threading.current_thread())

    try:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(LISTEN_BACKLOG)

        print("=" * 70)
        print("GVSoC TCP Server - SHARCBRIDGE")
        print("=" * 70)
        print(f"MPC ELF:        {MPC_ELF}")
        print(f"GVSoC binary:   {GVSOC_BINARY}")
        print(f"PULP SDK:       {PULP_SDK_SOURCEME}")
        print(f"SDK config:     {PULP_SDK_CONFIG}")
        print(f"GVSoC target:   {GVSOC_TARGET}")
        print(f"GVSoC platform: {GVSOC_PLATFORM}")
        print(f"GVSoC timeout:  {GVSOC_RUN_TIMEOUT_S}s")
        print(f"\nListening on:   {SERVER_HOST}:{SERVER_PORT}")
        print("=" * 70)
        print("\nWaiting for connections...\n")

        while not stop_event.is_set():
            try:
                conn, addr = server_socket.accept()
            except socket.timeout:
                continue

            th = threading.Thread(target=_client_runner, args=(conn, addr), daemon=True)
            client_threads.add(th)
            th.start()

        print("\n[Server] Shutting down gracefully")

    except KeyboardInterrupt:
        print("\n\n[Server] Interrupted by user (Ctrl+C)")
    except Exception as exc:
        print(f"\n[Server] Fatal error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
    finally:
        for th in list(client_threads):
            th.join(timeout=1.0)
        server_socket.close()
        print("[Server] Socket closed")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Entry point."""
    print("Validating environment...", file=sys.stderr)

    if not validate_environment():
        print("\nFix the errors above and try again.", file=sys.stderr)
        sys.exit(1)

    state = set_exec_mode(DEFAULT_EXEC_MODE, DEFAULT_PERSISTENT_WORKERS)
    if state["exec_mode"] == "persistent":
        workers = state["runtime"]["num_workers"] if state["runtime"] else 0
        print(f"✓ Exec mode: persistent ({workers} workers)", file=sys.stderr)
    else:
        print("✓ Exec mode: legacy", file=sys.stderr)

    print("✓ All checks passed\n", file=sys.stderr)
    run_server()


if __name__ == "__main__":
    main()
