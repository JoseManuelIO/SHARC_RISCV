#!/usr/bin/env python3
"""
GVSoC target-control script for persistent QP solves.

This script is launched by GVSoC with --control-script and exposes
a tiny UNIX-socket RPC:
  request  = <u32_le payload_size><payload_blob>
  response = <u32_le state_size><state_blob>

When payload_size == 0, script exits gracefully.
"""

import os
import socket
import struct
from pathlib import Path


QP_MAX_N = 32
QP_MAX_M = 64


def _int_env(name: str, default: int) -> int:
    try:
        v = int(os.environ.get(name, str(default)), 0)
    except Exception:
        v = default
    return v


def _get_done_flag_offset() -> int:
    off = 0
    off += struct.calcsize("<ii")
    off += struct.calcsize("<" + ("f" * (QP_MAX_N * QP_MAX_N)))
    off += struct.calcsize("<" + ("f" * QP_MAX_N))
    off += struct.calcsize("<" + ("f" * (QP_MAX_M * QP_MAX_N)))
    off += struct.calcsize("<" + ("f" * QP_MAX_M))
    off += struct.calcsize("<" + ("f" * QP_MAX_M))
    off += struct.calcsize("<" + ("f" * QP_MAX_N))
    off += struct.calcsize("<ifff")
    off += struct.calcsize("<" + ("f" * QP_MAX_N))
    off += struct.calcsize("<fff")
    # Tail ints: iterations, converged, status_code, output_n, output_m, output_cycles, done_flag, runtime_mode, heartbeat
    off += struct.calcsize("<iiiiii")
    return off


def _recv_exact(conn: socket.socket, size: int) -> bytes | None:
    out = bytearray()
    while len(out) < size:
        chunk = conn.recv(size - len(out))
        if not chunk:
            if len(out) == 0:
                return None
            raise ConnectionError("unexpected EOF on control socket")
        out.extend(chunk)
    return bytes(out)


def _send_blob(conn: socket.socket, blob: bytes) -> None:
    conn.sendall(len(blob).to_bytes(4, byteorder="little"))
    conn.sendall(blob)


def _resolve_proxy_arg(args):
    if len(args) == 1:
        return args[0]
    if len(args) >= 2:
        return args[1]
    raise RuntimeError("target_control requires GVSoC proxy argument")


def target_control(*args) -> int:
    gv = _resolve_proxy_arg(args)

    try:
        import gvsoc.gvsoc_control as gvsoc_control  # type: ignore
    except Exception:
        gvsoc_control = gv.gvsoc_control

    router = gvsoc_control.Router(gv)

    socket_path = os.environ.get("GVSOC_QP_CTRL_SOCKET_PATH", "/tmp/gvsoc_qp_ctrl.sock")
    shared_addr = _int_env("GVSOC_QP_CTRL_SHARED_ADDR", 0x1C010000)
    shared_size = _int_env("GVSOC_QP_CTRL_SHARED_SIZE", 0)
    step_ps = _int_env("GVSOC_QP_CTRL_STEP_PS", 1000000)
    max_steps = _int_env("GVSOC_QP_CTRL_MAX_STEPS", 64)
    done_flag_offset = _get_done_flag_offset()

    if shared_size <= 0:
        raise RuntimeError("invalid GVSOC_QP_CTRL_SHARED_SIZE")
    if step_ps <= 0:
        step_ps = 1000000
    if max_steps <= 0:
        max_steps = 64

    sock_path = Path(socket_path)
    try:
        sock_path.unlink(missing_ok=True)
    except Exception:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    server.settimeout(0.25)

    try:
        # Warm-up step so binary loading/startup side effects are done before first payload.
        gv.run(step_ps)

        while True:
            if gv.is_sim_finished():
                return 0

            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue

            with conn:
                header = _recv_exact(conn, 4)
                if header is None:
                    continue
                req_size = int.from_bytes(header, byteorder="little")
                if req_size == 0:
                    return 0
                if req_size < 0 or req_size > shared_size * 2:
                    raise RuntimeError(f"invalid request size={req_size}")

                payload = _recv_exact(conn, req_size)
                if payload is None:
                    raise RuntimeError("missing request payload")

                router.mem_write(shared_addr, len(payload), payload)

                steps = 0
                state = None
                done = 0
                while done != 1 and steps < max_steps:
                    gv.run(step_ps)
                    state = router.mem_read(shared_addr, shared_size)
                    done = struct.unpack_from("<i", state, done_flag_offset)[0]
                    steps += 1

                if state is None:
                    state = router.mem_read(shared_addr, shared_size)
                _send_blob(conn, state)
    finally:
        try:
            server.close()
        except Exception:
            pass
        try:
            sock_path.unlink(missing_ok=True)
        except Exception:
            pass
