#!/usr/bin/env python3
"""
CVA6 TCP server.

T2 scope:
- newline-delimited JSON transport
- commands: health, run_snapshot, shutdown
- stable request/response contract for the new SHARC-CVA6 flow
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
from dataclasses import asdict

from cva6_runtime_launcher import CVA6RuntimeLauncher, SnapshotInput


SERVER_HOST = os.environ.get("CVA6_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("CVA6_SERVER_PORT", "5001"))
LISTEN_BACKLOG = 32
CONNECTION_TIMEOUT_S = 5.0
MAX_BUFFER_BYTES = 2 * 1024 * 1024


def build_error(message: str, request_id=None, code: str = "BAD_REQUEST") -> dict:
    payload = {"status": "ERROR", "error_code": code, "error": message}
    if request_id is not None:
        payload["request_id"] = request_id
    return payload


def validate_request(payload: object) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload must be object"

    req_type = payload.get("type")
    if req_type not in {"health", "run_snapshot", "shutdown"}:
        return False, "type must be one of health/run_snapshot/shutdown"

    if req_type == "health":
        return True, ""
    if req_type == "shutdown":
        return True, ""

    if "request_id" not in payload:
        return False, "request_id is required"
    if not isinstance(payload.get("k"), int):
        return False, "k must be int"
    if not isinstance(payload.get("t"), (int, float)):
        return False, "t must be numeric"
    for key, expected_len in (("x", 3), ("w", 2), ("u_prev", 2)):
        value = payload.get(key)
        if not isinstance(value, list) or len(value) != expected_len:
            return False, f"{key} must be [{expected_len} numbers]"
        if not all(isinstance(v, (int, float)) for v in value):
            return False, f"{key} must be [{expected_len} numbers]"
    return True, ""


def send_json(conn: socket.socket, payload: dict) -> None:
    conn.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def handle_request(payload: dict, launcher: CVA6RuntimeLauncher, shutdown_event: threading.Event) -> dict:
    req_type = payload["type"]
    request_id = payload.get("request_id")

    if req_type == "health":
        resp = launcher.health()
        resp["request_id"] = request_id
        return resp
    if req_type == "shutdown":
        shutdown_event.set()
        return {"status": "SUCCESS", "request_id": request_id, "message": "shutdown requested"}

    snap = SnapshotInput(
        request_id=request_id,
        k=int(payload["k"]),
        t=float(payload["t"]),
        x=[float(v) for v in payload["x"]],
        w=[float(v) for v in payload["w"]],
        u_prev=[float(v) for v in payload["u_prev"]],
    )
    return launcher.run_snapshot(snap)


def serve_forever(host: str = SERVER_HOST, port: int = SERVER_PORT) -> None:
    launcher = CVA6RuntimeLauncher()
    shutdown_event = threading.Event()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen(LISTEN_BACKLOG)
            srv.settimeout(0.5)
            print(f"[CVA6 TCP] Listening on {host}:{port}", file=sys.stderr)

            while not shutdown_event.is_set():
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue

                with conn:
                    conn.settimeout(CONNECTION_TIMEOUT_S)
                    pending = b""
                    while not shutdown_event.is_set():
                        while b"\n" not in pending:
                            chunk = conn.recv(4096)
                            if not chunk:
                                pending = b""
                                break
                            pending += chunk
                            if len(pending) > MAX_BUFFER_BYTES:
                                send_json(conn, build_error("request too large"))
                                pending = b""
                                break
                        if not pending:
                            break

                        line, _, pending = pending.partition(b"\n")
                        try:
                            payload = json.loads(line.decode("utf-8"))
                        except Exception:
                            send_json(conn, build_error("invalid json"))
                            continue

                        ok, err = validate_request(payload)
                        if not ok:
                            send_json(conn, build_error(err, payload.get("request_id")))
                            continue

                        try:
                            response = handle_request(payload, launcher, shutdown_event)
                        except Exception as exc:
                            response = build_error(str(exc), payload.get("request_id"), code="BACKEND_ERROR")

                        send_json(conn, response)
    finally:
        launcher.close()


def main() -> None:
    serve_forever()


if __name__ == "__main__":
    main()
