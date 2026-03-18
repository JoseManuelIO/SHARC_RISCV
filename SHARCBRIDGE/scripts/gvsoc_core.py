#!/usr/bin/env python3
"""
GVSoC Core - Shared MPC execution logic.

This module contains logic shared by TCP and Flask transports:
- environment validation
- ELF patching for runtime inputs
- GVSoC execution
- stdout parsing into MPC response payload
"""

import re
import shutil
import struct
import subprocess
import sys
import time
import os
import threading
import socket
from pathlib import Path


# ============================================================================
# Shared Configuration
# ============================================================================

SERVER_HOST = os.environ.get("GVSOC_SERVER_HOST", "0.0.0.0")
try:
    SERVER_PORT = int(os.environ.get("GVSOC_PORT", "5000"))
except ValueError:
    SERVER_PORT = 5000

DOUBLE_NATIVE = os.environ.get("SHARC_DOUBLE_NATIVE", "0").strip().lower() in {"1", "true", "yes", "on"}
_DEFAULT_SDK_CONFIG = "pulp-open-double.sh" if DOUBLE_NATIVE else "pulp-open.sh"
# Keep target as pulp-open in both modes. The SDK config selects ISA details.
_DEFAULT_TARGET = "pulp-open"

PULP_SDK_CONFIG = os.environ.get("PULP_SDK_CONFIG", _DEFAULT_SDK_CONFIG)
GVSOC_TARGET = os.environ.get("GVSOC_TARGET", _DEFAULT_TARGET)
GVSOC_PLATFORM = os.environ.get("GVSOC_PLATFORM", "gvsoc")

try:
    GVSOC_RUN_TIMEOUT_S = int(os.environ.get("GVSOC_RUN_TIMEOUT_S", "10"))
except ValueError:
    GVSOC_RUN_TIMEOUT_S = 10

SHARCBRIDGE_DIR = Path.home() / "Repositorios" / "SHARC_RISCV" / "SHARCBRIDGE"
MPC_DIR = SHARCBRIDGE_DIR / "mpc"
MPC_ELF = MPC_DIR / "build" / "mpc_acc_controller.elf"
QP_RUNTIME_ELF = MPC_DIR / "build" / "qp_riscv_runtime.elf"
QP_TARGET_CONTROL_SCRIPT = SHARCBRIDGE_DIR / "scripts" / "gvsoc_qp_target_control.py"

VENV_ACTIVATE = Path.home() / "Repositorios" / "SHARC_RISCV" / "venv" / "bin" / "activate"

PULP_DIR = Path.home() / "Repositorios" / "SHARC_RISCV" / "PULP"
PULP_SDK_SOURCEME = PULP_DIR / "pulp-sdk" / "configs" / PULP_SDK_CONFIG
GVSOC_INSTALL_DIR = PULP_DIR / "gvsoc" / "install"
GVSOC_BINARY = GVSOC_INSTALL_DIR / "bin" / "gvsoc"

TOOLCHAIN_PREFIX = Path(os.environ.get("RISCV_TOOLCHAIN_PREFIX", "/opt/riscv"))
TOOLCHAIN_DIR = TOOLCHAIN_PREFIX / "bin"
OBJCOPY = TOOLCHAIN_DIR / "riscv32-unknown-elf-objcopy"
NM = TOOLCHAIN_DIR / "riscv32-unknown-elf-nm"
GCC = TOOLCHAIN_DIR / "riscv32-unknown-elf-gcc"

PATCHED_ELF = "/tmp/mpc_acc_patched.elf"
QP_PATCHED_ELF = "/tmp/qp_riscv_patched.elf"
QP_MAX_N = 32
QP_MAX_M = 64
QP_RESULT_TAIL_FIELDS = 16
try:
    QP_PERSISTENT_POLL_S = float(os.environ.get("GVSOC_QP_PERSISTENT_POLL_S", "0.001"))
except ValueError:
    QP_PERSISTENT_POLL_S = 0.001
try:
    QP_PERSISTENT_WAIT_TIMEOUT_S = float(os.environ.get("GVSOC_QP_PERSISTENT_WAIT_TIMEOUT_S", "8.0"))
except ValueError:
    QP_PERSISTENT_WAIT_TIMEOUT_S = 8.0
try:
    QP_PERSISTENT_PROXY_IO_TIMEOUT_S = float(os.environ.get("GVSOC_QP_PERSISTENT_PROXY_IO_TIMEOUT_S", "0.25"))
except ValueError:
    QP_PERSISTENT_PROXY_IO_TIMEOUT_S = 0.25
try:
    QP_PERSISTENT_STEP_PS = int(os.environ.get("GVSOC_QP_PERSISTENT_STEP_PS", "100000000"))
except ValueError:
    QP_PERSISTENT_STEP_PS = 100000000
if QP_PERSISTENT_STEP_PS <= 0:
    QP_PERSISTENT_STEP_PS = 100000000
try:
    QP_PERSISTENT_STEP_TIMEOUT_S = float(os.environ.get("GVSOC_QP_PERSISTENT_STEP_TIMEOUT_S", "2.0"))
except ValueError:
    QP_PERSISTENT_STEP_TIMEOUT_S = 2.0
try:
    QP_PERSISTENT_RUN_WINDOW_S = float(os.environ.get("GVSOC_QP_PERSISTENT_RUN_WINDOW_S", "0.05"))
except ValueError:
    QP_PERSISTENT_RUN_WINDOW_S = 0.05
if QP_PERSISTENT_RUN_WINDOW_S <= 0:
    QP_PERSISTENT_RUN_WINDOW_S = 0.05
try:
    QP_PERSISTENT_CONTROL_MAX_STEPS = int(os.environ.get("GVSOC_QP_PERSISTENT_CONTROL_MAX_STEPS", "1024"))
except ValueError:
    QP_PERSISTENT_CONTROL_MAX_STEPS = 1024
if QP_PERSISTENT_CONTROL_MAX_STEPS <= 0:
    QP_PERSISTENT_CONTROL_MAX_STEPS = 1024
QP_PERSISTENT_ALLOW_FALLBACK = os.environ.get("GVSOC_QP_PERSISTENT_ALLOW_FALLBACK", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
QP_PERSISTENT_DEBUG = os.environ.get("GVSOC_QP_PERSISTENT_DEBUG", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_metrics_lock = threading.Lock()
_gvsoc_spawn_count = 0
_elf_patch_count = 0


def reset_runtime_metrics() -> None:
    """Reset instrumentation counters for the current Python process."""
    global _gvsoc_spawn_count, _elf_patch_count
    with _metrics_lock:
        _gvsoc_spawn_count = 0
        _elf_patch_count = 0


def _bump_spawn_count() -> int:
    global _gvsoc_spawn_count
    with _metrics_lock:
        _gvsoc_spawn_count += 1
        return _gvsoc_spawn_count


def _bump_elf_patch_count() -> int:
    global _elf_patch_count
    with _metrics_lock:
        _elf_patch_count += 1
        return _elf_patch_count


def get_runtime_metrics_snapshot() -> dict:
    """Return current instrumentation snapshot."""
    with _metrics_lock:
        return {
            "gvsoc_spawn_count": _gvsoc_spawn_count,
            "elf_patch_count": _elf_patch_count,
        }


def _qp_debug_print(msg: str) -> None:
    if QP_PERSISTENT_DEBUG:
        print(msg, file=sys.stderr)


# ============================================================================
# Validation
# ============================================================================

def validate_environment() -> bool:
    """Check that required binaries/files exist."""
    errors = []

    if not MPC_ELF.exists():
        errors.append(f"MPC ELF not found: {MPC_ELF}")
        errors.append(f"  Build with: cd {MPC_DIR} && make")

    if not PULP_SDK_SOURCEME.exists():
        errors.append(f"PULP SDK config not found: {PULP_SDK_SOURCEME}")
        errors.append("  Override with env PULP_SDK_CONFIG=<config>.sh")

    if not GVSOC_BINARY.exists():
        errors.append(f"GVSoC binary not found: {GVSOC_BINARY}")
        errors.append("  Build GVSoC first: cd PULP/gvsoc && make all install")

    if DOUBLE_NATIVE and not toolchain_supports_ilp32d():
        errors.append("Double-native mode requested, but active toolchain has no ilp32d multilib.")
        errors.append(f"  Toolchain checked: {GCC}")
        errors.append("  Verify with: riscv32-unknown-elf-gcc -print-multi-lib")
        errors.append("  Then select/install a toolchain built with rv32* + ilp32d support.")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return False
    return True


def toolchain_supports_ilp32d() -> bool:
    """Return True if current GCC multilib includes ilp32d."""
    if not GCC.exists():
        return False
    try:
        result = subprocess.run([str(GCC), "-print-multi-lib"], capture_output=True, text=True, timeout=5)
    except Exception:
        return False
    if result.returncode != 0:
        return False
    return "@mabi=ilp32d" in result.stdout.lower()


# ============================================================================
# ELF Patching
# ============================================================================

_shared_addr = None


def get_shared_addr() -> int:
    """Get address of symbol 'shared' from ELF symbol table."""
    global _shared_addr
    if _shared_addr is not None:
        return _shared_addr

    try:
        result = subprocess.run([str(NM), str(MPC_ELF)], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if " D shared" in line or " d shared" in line:
                _shared_addr = int(line.split()[0], 16)
                print(f"[Core] Shared data at 0x{_shared_addr:08x}", file=sys.stderr)
                return _shared_addr
    except Exception as exc:
        print(f"[Core] WARNING: Could not read symbol table: {exc}", file=sys.stderr)

    _shared_addr = 0x1C010000
    print(f"[Core] Using default shared address: 0x{_shared_addr:08x}", file=sys.stderr)
    return _shared_addr


def patch_elf_with_params(k: int, t: float, x: list, w: list, u_prev: list | None = None) -> str:
    """Patch .shared_data section with runtime inputs; return patched ELF path."""
    _bump_elf_patch_count()

    if u_prev is None:
        u_prev = [0.0, 100.0]

    shutil.copy2(str(MPC_ELF), PATCHED_ELF)

    # Layout must match SharedData in mpc_acc_controller.c
    payload = struct.pack("<3f", x[0], x[1], x[2])
    payload += struct.pack("<2f", w[0], w[1])
    payload += struct.pack("<i", k)
    payload += struct.pack("<f", t)
    payload += struct.pack("<2f", u_prev[0], u_prev[1])

    raw_file = "/tmp/gvsoc_shared_data.bin"
    with open(raw_file, "wb") as f:
        f.write(payload)

    try:
        result = subprocess.run(
            [str(OBJCOPY), "--update-section", f".shared_data={raw_file}", PATCHED_ELF],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            print(f"[Core] WARNING: objcopy failed: {result.stderr}", file=sys.stderr)
            return str(MPC_ELF)
    except Exception as exc:
        print(f"[Core] WARNING: objcopy error: {exc}", file=sys.stderr)
        return str(MPC_ELF)

    return PATCHED_ELF


def _csc_to_dense_flat(rows: int, cols: int, colptr: list, rowind: list, data: list) -> list[float]:
    dense = [0.0] * (rows * cols)
    for c in range(cols):
        c0 = int(colptr[c])
        c1 = int(colptr[c + 1])
        for p in range(c0, c1):
            r = int(rowind[p])
            dense[r * cols + c] += float(data[p])
    return dense


_qp_shared_addr = None


def get_qp_shared_addr() -> int:
    """Get address of symbol 'shared' for QP runtime ELF."""
    global _qp_shared_addr
    if _qp_shared_addr is not None:
        return _qp_shared_addr

    try:
        result = subprocess.run([str(NM), str(QP_RUNTIME_ELF)], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if " D shared" in line or " d shared" in line:
                _qp_shared_addr = int(line.split()[0], 16)
                print(f"[Core] QP shared data at 0x{_qp_shared_addr:08x}", file=sys.stderr)
                return _qp_shared_addr
    except Exception as exc:
        print(f"[Core] WARNING: Could not read QP symbol table: {exc}", file=sys.stderr)

    _qp_shared_addr = 0x1C010000
    print(f"[Core] Using default QP shared address: 0x{_qp_shared_addr:08x}", file=sys.stderr)
    return _qp_shared_addr


def _build_qp_shared_blob(
    payload: dict,
    settings: dict | None = None,
    *,
    runtime_mode: int = 0,
    done_flag: int = 0,
) -> tuple[bytes, int, int]:
    """
    Build raw shared-data blob for qp_riscv_runtime.c.

    Layout must match QPSharedData in mpc/qp_riscv_runtime.c.
    """
    settings = settings or {}

    from qp_payload import validate_qp_payload

    ok, err = validate_qp_payload(payload)
    if not ok:
        raise ValueError(f"invalid qp payload: {err}")

    n = int(payload["n"])
    m = int(payload["m"])
    if n <= 0 or m <= 0 or n > QP_MAX_N or m > QP_MAX_M:
        raise ValueError(f"unsupported qp dimensions n={n}, m={m}, max=({QP_MAX_N},{QP_MAX_M})")

    P = _csc_to_dense_flat(
        rows=n,
        cols=n,
        colptr=payload["P_colptr"],
        rowind=payload["P_rowind"],
        data=payload["P_data"],
    )
    A = _csc_to_dense_flat(
        rows=m,
        cols=n,
        colptr=payload["A_colptr"],
        rowind=payload["A_rowind"],
        data=payload["A_data"],
    )

    q = [float(v) for v in payload["q"]]
    l = [float(v) for v in payload["l"]]
    u = [float(v) for v in payload["u"]]

    x0 = settings.get("x0")
    if not isinstance(x0, list) or len(x0) != n:
        x0 = [0.0] * n
    x0 = [float(v) for v in x0]

    max_iter = int(settings.get("max_iter", 200))
    tol = float(settings.get("tol", 1e-5))
    rho = float(settings.get("rho", 0.1))
    sigma = float(settings.get("sigma", 1e-8))
    if max_iter <= 0:
        max_iter = 200
    if tol <= 0:
        tol = 1e-5
    if rho <= 0:
        rho = 0.1
    if sigma < 0:
        sigma = 1e-8

    P_pad = P + [0.0] * (QP_MAX_N * QP_MAX_N - len(P))
    q_pad = q + [0.0] * (QP_MAX_N - len(q))
    A_pad = A + [0.0] * (QP_MAX_M * QP_MAX_N - len(A))
    l_pad = l + [0.0] * (QP_MAX_M - len(l))
    u_pad = u + [0.0] * (QP_MAX_M - len(u))
    x0_pad = x0 + [0.0] * (QP_MAX_N - len(x0))

    # Output fields zero-initialized.
    x_out_pad = [0.0] * QP_MAX_N

    blob = b""
    blob += struct.pack("<ii", n, m)
    blob += struct.pack("<" + ("f" * (QP_MAX_N * QP_MAX_N)), *P_pad)
    blob += struct.pack("<" + ("f" * QP_MAX_N), *q_pad)
    blob += struct.pack("<" + ("f" * (QP_MAX_M * QP_MAX_N)), *A_pad)
    blob += struct.pack("<" + ("f" * QP_MAX_M), *l_pad)
    blob += struct.pack("<" + ("f" * QP_MAX_M), *u_pad)
    blob += struct.pack("<" + ("f" * QP_MAX_N), *x0_pad)
    blob += struct.pack("<ifff", max_iter, tol, rho, sigma)
    blob += struct.pack("<" + ("f" * QP_MAX_N), *x_out_pad)
    blob += struct.pack("<fff", 0.0, 0.0, 0.0)
    blob += struct.pack(
        "<" + ("i" * QP_RESULT_TAIL_FIELDS),
        # Legacy tail (kept stable for done_flag/runtime_mode offset)
        0,  # iterations
        0,  # converged
        0,  # status_code
        0,  # output_n
        0,  # output_m
        0,  # output_cycles
        int(done_flag),
        int(runtime_mode),
        0,  # heartbeat
        # Extended hardware counters
        0,  # output_instret
        0,  # output_ld_stall
        0,  # output_jmp_stall
        0,  # output_stall_total
        0,  # output_imiss
        0,  # output_branch
        0,  # output_taken_branch
    )

    return blob, n, m


def _decode_qp_shared_blob(blob: bytes, fallback_n: int = 0, fallback_m: int = 0) -> dict:
    if not isinstance(blob, (bytes, bytearray)):
        raise ValueError("qp shared blob must be bytes")

    off = 0
    n, m = struct.unpack_from("<ii", blob, off)
    off += struct.calcsize("<ii")

    off += struct.calcsize("<" + ("f" * (QP_MAX_N * QP_MAX_N)))
    off += struct.calcsize("<" + ("f" * QP_MAX_N))
    off += struct.calcsize("<" + ("f" * (QP_MAX_M * QP_MAX_N)))
    off += struct.calcsize("<" + ("f" * QP_MAX_M))
    off += struct.calcsize("<" + ("f" * QP_MAX_M))
    off += struct.calcsize("<" + ("f" * QP_MAX_N))
    off += struct.calcsize("<ifff")

    x = list(struct.unpack_from("<" + ("f" * QP_MAX_N), blob, off))
    off += struct.calcsize("<" + ("f" * QP_MAX_N))
    cost, primal_residual, dual_residual = struct.unpack_from("<fff", blob, off)
    off += struct.calcsize("<fff")
    tail_fields = QP_RESULT_TAIL_FIELDS
    if len(blob) < off + struct.calcsize("<" + ("i" * tail_fields)):
        # Backward compatibility for older QP runtime blobs.
        tail_fields = 9
    tail = struct.unpack_from("<" + ("i" * tail_fields), blob, off)
    (
        iterations,
        converged,
        status_code,
        output_n,
        output_m,
        output_cycles,
        done_flag,
        runtime_mode,
        heartbeat,
        *tail_extra,
    ) = tail

    output_instret = int(tail_extra[0]) if len(tail_extra) > 0 else 0
    output_ld_stall = int(tail_extra[1]) if len(tail_extra) > 1 else 0
    output_jmp_stall = int(tail_extra[2]) if len(tail_extra) > 2 else 0
    output_imiss = int(tail_extra[4]) if len(tail_extra) > 4 else 0
    output_stall_total = int(tail_extra[3]) if len(tail_extra) > 3 else (output_ld_stall + output_jmp_stall + output_imiss)
    output_branch = int(tail_extra[5]) if len(tail_extra) > 5 else 0
    output_taken_branch = int(tail_extra[6]) if len(tail_extra) > 6 else 0

    if output_n > 0:
        n = output_n
    if output_m > 0:
        m = output_m
    if n <= 0:
        n = fallback_n
    if m <= 0:
        m = fallback_m
    n = max(0, min(int(n), QP_MAX_N))
    m = max(0, min(int(m), QP_MAX_M))

    status = "BAD_DIM"
    if int(status_code) == 0:
        status = "OPTIMAL"
    elif int(status_code) == 1:
        status = "MAX_ITER"
    elif int(status_code) == -2:
        status = "FACTOR_FAIL"

    cpi = float(output_cycles) / float(output_instret) if int(output_instret) > 0 else 0.0
    ipc = float(output_instret) / float(output_cycles) if int(output_cycles) > 0 else 0.0

    return {
        "status": status,
        "status_code": int(status_code),
        "x": [float(v) for v in x[:n]],
        "cost": float(cost),
        "iterations": int(iterations),
        "converged": int(converged),
        "cycles": int(output_cycles),
        "primal_residual": float(primal_residual),
        "dual_residual": float(dual_residual),
        "n": int(n),
        "m": int(m),
        "done_flag": int(done_flag),
        "runtime_mode": int(runtime_mode),
        "heartbeat": int(heartbeat),
        "instret": int(output_instret),
        "ld_stall": int(output_ld_stall),
        "jmp_stall": int(output_jmp_stall),
        "stall_total": int(output_stall_total),
        "imiss": int(output_imiss),
        "branch": int(output_branch),
        "taken_branch": int(output_taken_branch),
        "cpi": float(cpi),
        "ipc": float(ipc),
    }


def patch_qp_elf_with_payload(
    payload: dict,
    settings: dict | None = None,
    *,
    runtime_mode: int = 0,
    done_flag: int = 0,
    patched_elf_path: str | None = None,
) -> str:
    """
    Patch QP runtime ELF with full QP payload.

    Shared layout must match QPSharedData in mpc/qp_riscv_runtime.c.
    """
    _bump_elf_patch_count()

    if not QP_RUNTIME_ELF.exists():
        raise FileNotFoundError(
            f"QP runtime ELF not found: {QP_RUNTIME_ELF}. "
            f"Build with: bash SHARCBRIDGE/scripts/build_qp_runtime_profile.sh "
            f"{'double' if DOUBLE_NATIVE else 'single'}"
        )

    blob, _, _ = _build_qp_shared_blob(
        payload,
        settings=settings,
        runtime_mode=runtime_mode,
        done_flag=done_flag,
    )

    path = patched_elf_path or QP_PATCHED_ELF
    shutil.copy2(str(QP_RUNTIME_ELF), path)
    raw_file = "/tmp/gvsoc_qp_shared_data.bin"
    with open(raw_file, "wb") as f:
        f.write(blob)

    result = subprocess.run(
        [str(OBJCOPY), "--update-section", f".shared_data={raw_file}", path],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(f"objcopy failed while patching QP ELF: {result.stderr.strip()}")

    return path


# ============================================================================
# MPC execution and parsing
# ============================================================================

_NUM_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _parse_mpc_output(output: str) -> dict:
    u = [0.0, 0.0]
    cost = 0.0
    iters = 0
    cycles = 0
    status = "UNKNOWN"

    u_match = re.search(rf"U=({_NUM_RE}),({_NUM_RE})", output)
    if u_match:
        u = [float(u_match.group(1)), float(u_match.group(2))]

    cost_match = re.search(rf"COST=({_NUM_RE})", output)
    if cost_match:
        cost = float(cost_match.group(1))

    iter_match = re.search(r"ITER=(\d+)", output)
    if iter_match:
        iters = int(iter_match.group(1))

    cycles_match = re.search(r"CYCLES=(\d+)", output)
    if cycles_match:
        cycles = int(cycles_match.group(1))

    status_match = re.search(r"STATUS=(\w+)", output)
    if status_match:
        status = status_match.group(1)

    if "MPC_START" not in output:
        status = "NO_START"

    return {
        "u": u,
        "cost": cost,
        "iterations": iters,
        "cycles": cycles,
        "status": status,
    }


def run_gvsoc_mpc(k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
    """
    Execute one MPC computation in GVSoC and parse result payload.
    Returns dict with keys: k, u, cost, status, iterations, cycles, t_delay.
    """
    if u_prev is None:
        u_prev = [0.0, 100.0]

    elf_path = patch_elf_with_params(k, t, x, w, u_prev)
    spawn_count = _bump_spawn_count()
    metrics = get_runtime_metrics_snapshot()

    cmd = f"""
    source {VENV_ACTIVATE} && \\
    source {PULP_SDK_SOURCEME} && \\
    timeout {GVSOC_RUN_TIMEOUT_S} {GVSOC_BINARY} \\
        --target={GVSOC_TARGET} \\
        --platform={GVSOC_PLATFORM} \\
        --binary={elf_path} \\
        run
    """

    t_start = time.perf_counter()
    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            cwd=str(MPC_DIR),
        )
        t_delay = time.perf_counter() - t_start
    except subprocess.TimeoutExpired:
        t_delay = time.perf_counter() - t_start
        out = {
            "k": k,
            "u": [0.0, 100.0],
            "cost": 0.0,
            "status": "TIMEOUT",
            "iterations": 0,
            "cycles": 0,
            "t_delay": t_delay,
        }
        out.update(metrics)
        out["gvsoc_spawn_seq"] = spawn_count
        return out
    except Exception as exc:
        t_delay = time.perf_counter() - t_start
        print(f"[Core] ERROR running GVSoC: {exc}", file=sys.stderr)
        out = {
            "k": k,
            "u": [0.0, 100.0],
            "cost": 0.0,
            "status": "ERROR",
            "iterations": 0,
            "cycles": 0,
            "t_delay": t_delay,
        }
        out.update(metrics)
        out["gvsoc_spawn_seq"] = spawn_count
        return out

    parsed = _parse_mpc_output(result.stdout)
    if result.returncode != 0:
        out = {
            "k": k,
            "u": [0.0, 100.0],
            "cost": 0.0,
            "status": "ERROR",
            "iterations": 0,
            "cycles": 0,
            "t_delay": t_delay,
            "error": (result.stderr or result.stdout or "").strip(),
        }
        out.update(metrics)
        out["gvsoc_spawn_seq"] = spawn_count
        print(
            f"[Core] ERROR non-zero GVSoC exit code={result.returncode}: "
            f"{(result.stderr or '').strip()}",
            file=sys.stderr,
        )
        return out

    out = {
        "k": k,
        "u": parsed["u"],
        "cost": parsed["cost"],
        "status": parsed["status"],
        "iterations": parsed["iterations"],
        "cycles": parsed["cycles"],
        "t_delay": t_delay,
    }
    out.update(metrics)
    out["gvsoc_spawn_seq"] = spawn_count
    print(
        f"[Core] metrics k={k} spawn_count={metrics['gvsoc_spawn_count']} "
        f"elf_patch_count={metrics['elf_patch_count']}",
        file=sys.stderr,
    )
    return out


def _parse_qp_output(output: str) -> dict:
    x = []
    cost = 0.0
    iters = 0
    cycles = 0
    status = "UNKNOWN"
    primal_residual = 0.0
    dual_residual = 0.0
    n = 0
    m = 0
    instret = 0
    ld_stall = 0
    jmp_stall = 0
    stall_total = 0
    imiss = 0
    branch = 0
    taken_branch = 0

    n_match = re.search(r"N=(\d+)", output)
    if n_match:
        n = int(n_match.group(1))
    m_match = re.search(r"M=(\d+)", output)
    if m_match:
        m = int(m_match.group(1))

    x_match = re.search(r"X=([^\n\r]+)", output)
    if x_match:
        raw = x_match.group(1).strip()
        if raw:
            x = [float(v.strip()) for v in raw.split(",") if v.strip() != ""]

    cost_match = re.search(rf"COST=({_NUM_RE})", output)
    if cost_match:
        cost = float(cost_match.group(1))

    iter_match = re.search(r"ITER=(\d+)", output)
    if iter_match:
        iters = int(iter_match.group(1))

    cycles_match = re.search(r"CYCLES=(\d+)", output)
    if cycles_match:
        cycles = int(cycles_match.group(1))

    instret_match = re.search(r"INSTRET=(\d+)", output)
    if instret_match:
        instret = int(instret_match.group(1))

    ld_stall_match = re.search(r"LD_STALL=(\d+)", output)
    if ld_stall_match:
        ld_stall = int(ld_stall_match.group(1))

    jmp_stall_match = re.search(r"JMP_STALL=(\d+)", output)
    if jmp_stall_match:
        jmp_stall = int(jmp_stall_match.group(1))

    imiss_match = re.search(r"IMISS=(\d+)", output)
    if imiss_match:
        imiss = int(imiss_match.group(1))

    branch_match = re.search(r"BRANCH=(\d+)", output)
    if branch_match:
        branch = int(branch_match.group(1))

    taken_branch_match = re.search(r"TAKEN_BRANCH=(\d+)", output)
    if taken_branch_match:
        taken_branch = int(taken_branch_match.group(1))

    stall_total_match = re.search(r"STALL_TOTAL=(\d+)", output)
    if stall_total_match:
        stall_total = int(stall_total_match.group(1))
    else:
        stall_total = ld_stall + jmp_stall + imiss

    prim_match = re.search(rf"PRIMAL_RES=({_NUM_RE})", output)
    if prim_match:
        primal_residual = float(prim_match.group(1))

    dual_match = re.search(rf"DUAL_RES=({_NUM_RE})", output)
    if dual_match:
        dual_residual = float(dual_match.group(1))

    status_match = re.search(r"STATUS=(\w+)", output)
    if status_match:
        status = status_match.group(1)

    if "QP_START" not in output:
        status = "NO_START"

    cpi = float(cycles) / float(instret) if instret > 0 else 0.0
    ipc = float(instret) / float(cycles) if cycles > 0 else 0.0

    return {
        "x": x,
        "cost": cost,
        "iterations": iters,
        "cycles": cycles,
        "status": status,
        "primal_residual": primal_residual,
        "dual_residual": dual_residual,
        "n": n,
        "m": m,
        "instret": instret,
        "ld_stall": ld_stall,
        "jmp_stall": jmp_stall,
        "stall_total": stall_total,
        "imiss": imiss,
        "branch": branch,
        "taken_branch": taken_branch,
        "cpi": cpi,
        "ipc": ipc,
    }


def _get_qp_shared_blob_size() -> int:
    return (
        struct.calcsize("<ii")
        + struct.calcsize("<" + ("f" * (QP_MAX_N * QP_MAX_N)))
        + struct.calcsize("<" + ("f" * QP_MAX_N))
        + struct.calcsize("<" + ("f" * (QP_MAX_M * QP_MAX_N)))
        + struct.calcsize("<" + ("f" * QP_MAX_M))
        + struct.calcsize("<" + ("f" * QP_MAX_M))
        + struct.calcsize("<" + ("f" * QP_MAX_N))
        + struct.calcsize("<ifff")
        + struct.calcsize("<" + ("f" * QP_MAX_N))
        + struct.calcsize("<fff")
        + struct.calcsize("<" + ("i" * QP_RESULT_TAIL_FIELDS))
    )


class QPPersistentSession:
    """Persistent GVSoC session for qp_solve with memory-level request updates."""

    def __init__(self, worker_id: int = 0):
        self.worker_id = int(worker_id)
        self._process = None
        self._proxy = None
        self._router = None
        self._port = None
        self._ctrl_socket_path = f"/tmp/gvsoc_qp_ctrl_w{self.worker_id}_{os.getpid()}.sock"
        self._shared_addr = None
        self._spawn_seq = None
        self._shared_size = _get_qp_shared_blob_size()
        self._lock = threading.RLock()
        self._patched_elf_path = f"/tmp/qp_riscv_patched_w{self.worker_id}_{os.getpid()}.elf"

    def _pick_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])

    def _wait_proxy_ready(self, timeout_s: float = 5.0) -> None:
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(f"persistent GVSoC exited early rc={self._process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", int(self._port)), timeout=0.2):
                    return
            except Exception:
                time.sleep(0.05)
        raise TimeoutError("persistent GVSoC proxy did not become ready")

    def _wait_control_socket_ready(self, timeout_s: float = 5.0) -> None:
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(f"persistent GVSoC exited early rc={self._process.returncode}")
            if os.path.exists(self._ctrl_socket_path):
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.settimeout(0.2)
                        s.connect(self._ctrl_socket_path)
                    return
                except Exception:
                    pass
            time.sleep(0.05)
        raise TimeoutError("persistent GVSoC control socket did not become ready")

    def _ensure_control_api(self):
        install_python = GVSOC_INSTALL_DIR / "python"
        if str(install_python) not in sys.path:
            sys.path.insert(0, str(install_python))
        import gvsoc.gvsoc_control as gvsoc_control  # type: ignore

        return gvsoc_control

    def _start(self, payload: dict, settings: dict | None = None) -> None:
        self._port = self._pick_free_port()
        self._shared_addr = get_qp_shared_addr()
        try:
            os.unlink(self._ctrl_socket_path)
        except FileNotFoundError:
            pass

        patch_qp_elf_with_payload(
            payload,
            settings=settings,
            runtime_mode=1,
            done_flag=1,
            patched_elf_path=self._patched_elf_path,
        )
        self._spawn_seq = _bump_spawn_count()

        cmd = f"""
        source {VENV_ACTIVATE} && \\
        source {PULP_SDK_SOURCEME} && \\
        export GVSOC_QP_CTRL_SOCKET_PATH={self._ctrl_socket_path} && \\
        export GVSOC_QP_CTRL_SHARED_ADDR=0x{int(self._shared_addr):08x} && \\
        export GVSOC_QP_CTRL_SHARED_SIZE={int(self._shared_size)} && \\
        export GVSOC_QP_CTRL_STEP_PS={int(QP_PERSISTENT_STEP_PS)} && \\
        export GVSOC_QP_CTRL_MAX_STEPS={int(QP_PERSISTENT_CONTROL_MAX_STEPS)} && \\
        {GVSOC_BINARY} \\
            --target={GVSOC_TARGET} \\
            --platform={GVSOC_PLATFORM} \\
            --binary={self._patched_elf_path} \\
            --control-script={QP_TARGET_CONTROL_SCRIPT} \\
            run
        """
        self._process = subprocess.Popen(
            ["bash", "-c", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(MPC_DIR),
        )
        self._wait_control_socket_ready(timeout_s=max(3.0, float(GVSOC_RUN_TIMEOUT_S)))
        print(
            f"[Core] QP persistent worker={self.worker_id} started control_socket={self._ctrl_socket_path} "
            f"shared=0x{int(self._shared_addr):08x}",
            file=sys.stderr,
        )

    def _recv_exact(self, sock_obj: socket.socket, size: int) -> bytes:
        out = bytearray()
        while len(out) < size:
            chunk = sock_obj.recv(size - len(out))
            if not chunk:
                raise ConnectionError("persistent control socket closed unexpectedly")
            out.extend(chunk)
        return bytes(out)

    def _solve_via_target_control(self, blob: bytes, timeout_s: float) -> bytes:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock_obj:
            sock_obj.settimeout(max(0.05, float(timeout_s)))
            sock_obj.connect(self._ctrl_socket_path)
            sock_obj.sendall(len(blob).to_bytes(4, byteorder="little"))
            sock_obj.sendall(blob)
            raw_len = self._recv_exact(sock_obj, 4)
            n = int.from_bytes(raw_len, byteorder="little")
            if n <= 0 or n > self._shared_size * 2:
                raise RuntimeError(f"invalid control response size={n}")
            return self._recv_exact(sock_obj, n)

    def _read_state(self, fallback_n: int, fallback_m: int) -> dict:
        raw = self._proxy_call(
            self._router.mem_read,
            int(self._shared_addr),
            int(self._shared_size),
            op_name="mem_read",
        )
        return _decode_qp_shared_blob(raw, fallback_n=fallback_n, fallback_m=fallback_m)

    def _write_payload(self, payload: dict, settings: dict | None = None) -> None:
        blob, _, _ = _build_qp_shared_blob(payload, settings=settings, runtime_mode=1, done_flag=0)
        self._proxy_call(
            self._router.mem_write,
            int(self._shared_addr),
            len(blob),
            blob,
            op_name="mem_write",
        )

    def _run_step(self) -> None:
        if self._proxy is None:
            raise RuntimeError("persistent GVSoC proxy not initialized")
        # External proxy mode cannot reliably use synchronous run(step).
        # Drive a short async run window and force a stop before memory inspection.
        self._proxy_call(
            self._proxy.run,
            op_name="run_async",
            timeout_s=max(0.01, float(QP_PERSISTENT_STEP_TIMEOUT_S)),
        )
        time.sleep(float(QP_PERSISTENT_RUN_WINDOW_S))
        self._proxy_call(
            self._proxy.stop,
            op_name="stop_after_run",
            timeout_s=max(0.01, float(QP_PERSISTENT_STEP_TIMEOUT_S)),
        )

    def _proxy_call(self, fn, *args, op_name: str, timeout_s: float | None = None):
        result = {}
        error = {}
        timeout_val = max(
            0.01,
            float(QP_PERSISTENT_PROXY_IO_TIMEOUT_S if timeout_s is None else timeout_s),
        )

        def _target():
            try:
                result["value"] = fn(*args)
            except Exception as exc:  # pragma: no cover - transport dependent
                error["exc"] = exc

        th = threading.Thread(target=_target, daemon=True)
        th.start()
        th.join(timeout=timeout_val)

        if th.is_alive():
            raise TimeoutError(
                f"persistent GVSoC proxy {op_name} timeout after "
                f"{timeout_val:.3f}s"
            )
        if "exc" in error:
            raise error["exc"]
        return result.get("value")

    def _wait_done(self, fallback_n: int, fallback_m: int, timeout_s: float) -> dict:
        deadline = time.perf_counter() + timeout_s
        last_state = None
        while time.perf_counter() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(f"persistent GVSoC exited rc={self._process.returncode}")
            self._run_step()
            state = self._read_state(fallback_n=fallback_n, fallback_m=fallback_m)
            last_state = state
            if int(state.get("done_flag", 0)) == 1:
                return state
        hb = int(last_state.get("heartbeat", -1)) if isinstance(last_state, dict) else -1
        done = int(last_state.get("done_flag", -1)) if isinstance(last_state, dict) else -1
        raise TimeoutError(
            "persistent GVSoC qp_solve timeout waiting done_flag "
            f"(step_ps={int(QP_PERSISTENT_STEP_PS)}, done={done}, heartbeat={hb})"
        )

    def solve(self, payload: dict, settings: dict | None = None) -> dict:
        settings = settings or {}
        n = int(payload.get("n", 0)) if isinstance(payload, dict) else 0
        m = int(payload.get("m", 0)) if isinstance(payload, dict) else 0
        t_start = time.perf_counter()

        with self._lock:
            try:
                if self._process is None:
                    self._start(payload, settings=settings)
                blob, _, _ = _build_qp_shared_blob(payload, settings=settings, runtime_mode=1, done_flag=0)
                tail = struct.unpack_from(
                    "<" + ("i" * QP_RESULT_TAIL_FIELDS),
                    blob,
                    len(blob) - struct.calcsize("<" + ("i" * QP_RESULT_TAIL_FIELDS)),
                )
                _qp_debug_print(
                    f"[Core] QP persistent send worker={self.worker_id} done={int(tail[6])} runtime={int(tail[7])}",
                )
                raw = self._solve_via_target_control(
                    blob,
                    timeout_s=max(0.05, float(QP_PERSISTENT_WAIT_TIMEOUT_S)),
                )
                state = _decode_qp_shared_blob(raw, fallback_n=n, fallback_m=m)
                _qp_debug_print(
                    f"[Core] QP persistent recv worker={self.worker_id} status={state.get('status')} "
                    f"done={int(state.get('done_flag', -1))} hb={int(state.get('heartbeat', -1))} "
                    f"n={int(state.get('n', -1))} m={int(state.get('m', -1))} "
                    f"mode={int(state.get('runtime_mode', -1))}",
                )
                if int(state.get("done_flag", 0)) != 1:
                    raise TimeoutError(
                        "persistent GVSoC qp_solve timeout waiting done_flag "
                        f"(done={int(state.get('done_flag', -1))}, heartbeat={int(state.get('heartbeat', -1))})"
                    )
            except TimeoutError as exc:
                print(
                    f"[Core] TIMEOUT persistent GVSoC QP worker={self.worker_id}: {exc}",
                    file=sys.stderr,
                )
                self.close()
                return {
                    "status": "TIMEOUT",
                    "x": [0.0] * max(0, n),
                    "cost": 0.0,
                    "iterations": 0,
                    "converged": 0,
                    "cycles": 0,
                    "t_delay": time.perf_counter() - t_start,
                    "primal_residual": 0.0,
                    "dual_residual": 0.0,
                    "n": n,
                    "m": m,
                    "instret": 0,
                    "ld_stall": 0,
                    "jmp_stall": 0,
                    "stall_total": 0,
                    "imiss": 0,
                    "branch": 0,
                    "taken_branch": 0,
                    "cpi": 0.0,
                    "ipc": 0.0,
                }
            except Exception as exc:
                print(f"[Core] ERROR persistent GVSoC QP: {exc}", file=sys.stderr)
                self.close()
                return {
                    "status": "ERROR",
                    "x": [0.0] * max(0, n),
                    "cost": 0.0,
                    "iterations": 0,
                    "converged": 0,
                    "cycles": 0,
                    "t_delay": time.perf_counter() - t_start,
                    "primal_residual": 0.0,
                    "dual_residual": 0.0,
                    "n": n,
                    "m": m,
                    "instret": 0,
                    "ld_stall": 0,
                    "jmp_stall": 0,
                    "stall_total": 0,
                    "imiss": 0,
                    "branch": 0,
                    "taken_branch": 0,
                    "cpi": 0.0,
                    "ipc": 0.0,
                }

        out = {
            "status": state["status"],
            "x": state["x"],
            "cost": state["cost"],
            "iterations": state["iterations"],
            "converged": 1 if state["status"] == "OPTIMAL" else int(state["converged"]),
            "cycles": state["cycles"],
            "t_delay": time.perf_counter() - t_start,
            "primal_residual": state["primal_residual"],
            "dual_residual": state["dual_residual"],
            "n": state["n"],
            "m": state["m"],
            "instret": state["instret"],
            "ld_stall": state["ld_stall"],
            "jmp_stall": state["jmp_stall"],
            "stall_total": state["stall_total"],
            "imiss": state["imiss"],
            "branch": state["branch"],
            "taken_branch": state["taken_branch"],
            "cpi": state["cpi"],
            "ipc": state["ipc"],
        }
        out.update(get_runtime_metrics_snapshot())
        if self._spawn_seq is not None:
            out["gvsoc_spawn_seq"] = int(self._spawn_seq)
        return out

    def close(self) -> None:
        with self._lock:
            if self._ctrl_socket_path and os.path.exists(self._ctrl_socket_path):
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock_obj:
                        sock_obj.settimeout(0.2)
                        sock_obj.connect(self._ctrl_socket_path)
                        sock_obj.sendall((0).to_bytes(4, byteorder="little"))
                except Exception:
                    pass

            if self._proxy is not None:
                try:
                    self._proxy.close()
                except Exception:
                    pass
                self._proxy = None
                self._router = None

            if self._process is not None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=2)
                except Exception:
                    try:
                        self._process.kill()
                        self._process.wait(timeout=1)
                    except Exception:
                        pass
                self._process = None
            self._port = None
            self._shared_addr = None
            self._spawn_seq = None
            if self._ctrl_socket_path:
                try:
                    os.unlink(self._ctrl_socket_path)
                except FileNotFoundError:
                    pass


def build_qp_persistent_compute_fn(worker_id: int):
    """Factory helper for GenericPersistentRuntimePool."""
    session = QPPersistentSession(worker_id=worker_id)

    def _compute(payload: dict, settings: dict | None = None) -> dict:
        out = session.solve(payload, settings=settings)
        if QP_PERSISTENT_ALLOW_FALLBACK and out.get("status") in {"TIMEOUT", "ERROR"}:
            print(
                f"[Core] QP persistent fallback worker={worker_id} status={out.get('status')} -> legacy run_gvsoc_qp",
                file=sys.stderr,
            )
            return run_gvsoc_qp(payload, settings=settings)
        return out

    def _close() -> None:
        session.close()

    setattr(_compute, "_close", _close)
    return _compute


def run_gvsoc_qp(payload: dict, settings: dict | None = None) -> dict:
    """
    Execute one QP solve in GVSoC using dedicated RISC-V runtime solver.
    Returns: status, x, cost, iterations, cycles, residuals, t_delay.
    """
    settings = settings or {}
    n = int(payload.get("n", 0)) if isinstance(payload, dict) else 0
    m = int(payload.get("m", 0)) if isinstance(payload, dict) else 0

    elf_path = patch_qp_elf_with_payload(payload, settings=settings)
    spawn_count = _bump_spawn_count()
    metrics = get_runtime_metrics_snapshot()

    cmd = f"""
    source {VENV_ACTIVATE} && \\
    source {PULP_SDK_SOURCEME} && \\
    timeout {GVSOC_RUN_TIMEOUT_S} {GVSOC_BINARY} \\
        --target={GVSOC_TARGET} \\
        --platform={GVSOC_PLATFORM} \\
        --binary={elf_path} \\
        run
    """

    t_start = time.perf_counter()
    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            cwd=str(MPC_DIR),
        )
        t_delay = time.perf_counter() - t_start
    except subprocess.TimeoutExpired:
        t_delay = time.perf_counter() - t_start
        out = {
            "status": "TIMEOUT",
            "x": [0.0] * max(0, n),
            "cost": 0.0,
            "iterations": 0,
            "converged": 0,
            "cycles": 0,
            "t_delay": t_delay,
            "primal_residual": 0.0,
            "dual_residual": 0.0,
            "n": n,
            "m": m,
            "instret": 0,
            "ld_stall": 0,
            "jmp_stall": 0,
            "stall_total": 0,
            "imiss": 0,
            "branch": 0,
            "taken_branch": 0,
            "cpi": 0.0,
            "ipc": 0.0,
        }
        out.update(metrics)
        out["gvsoc_spawn_seq"] = spawn_count
        return out
    except Exception as exc:
        t_delay = time.perf_counter() - t_start
        print(f"[Core] ERROR running GVSoC QP solver: {exc}", file=sys.stderr)
        out = {
            "status": "ERROR",
            "x": [0.0] * max(0, n),
            "cost": 0.0,
            "iterations": 0,
            "converged": 0,
            "cycles": 0,
            "t_delay": t_delay,
            "primal_residual": 0.0,
            "dual_residual": 0.0,
            "n": n,
            "m": m,
            "instret": 0,
            "ld_stall": 0,
            "jmp_stall": 0,
            "stall_total": 0,
            "imiss": 0,
            "branch": 0,
            "taken_branch": 0,
            "cpi": 0.0,
            "ipc": 0.0,
        }
        out.update(metrics)
        out["gvsoc_spawn_seq"] = spawn_count
        return out

    parsed = _parse_qp_output(result.stdout)
    if result.returncode != 0:
        out = {
            "status": "ERROR",
            "x": [0.0] * max(0, n),
            "cost": 0.0,
            "iterations": 0,
            "converged": 0,
            "cycles": 0,
            "t_delay": t_delay,
            "primal_residual": 0.0,
            "dual_residual": 0.0,
            "n": n,
            "m": m,
            "error": (result.stderr or result.stdout or "").strip(),
            "instret": 0,
            "ld_stall": 0,
            "jmp_stall": 0,
            "stall_total": 0,
            "imiss": 0,
            "branch": 0,
            "taken_branch": 0,
            "cpi": 0.0,
            "ipc": 0.0,
        }
        out.update(metrics)
        out["gvsoc_spawn_seq"] = spawn_count
        print(
            f"[Core] ERROR non-zero GVSoC exit code={result.returncode} (QP): "
            f"{(result.stderr or '').strip()}",
            file=sys.stderr,
        )
        return out

    out = {
        "status": parsed["status"],
        "x": parsed["x"],
        "cost": parsed["cost"],
        "iterations": parsed["iterations"],
        "converged": 1 if parsed["status"] == "OPTIMAL" else 0,
        "cycles": parsed["cycles"],
        "t_delay": t_delay,
        "primal_residual": parsed["primal_residual"],
        "dual_residual": parsed["dual_residual"],
        "n": parsed["n"] if parsed["n"] > 0 else n,
        "m": parsed["m"] if parsed["m"] > 0 else m,
        "instret": parsed["instret"],
        "ld_stall": parsed["ld_stall"],
        "jmp_stall": parsed["jmp_stall"],
        "stall_total": parsed["stall_total"],
        "imiss": parsed["imiss"],
        "branch": parsed["branch"],
        "taken_branch": parsed["taken_branch"],
        "cpi": parsed["cpi"],
        "ipc": parsed["ipc"],
    }
    out.update(metrics)
    out["gvsoc_spawn_seq"] = spawn_count
    print(
        f"[Core] QP metrics spawn_count={metrics['gvsoc_spawn_count']} "
        f"elf_patch_count={metrics['elf_patch_count']} status={out['status']} "
        f"iters={out['iterations']} cycles={out['cycles']}",
        file=sys.stderr,
    )
    return out
