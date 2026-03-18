#!/usr/bin/env python3
"""
CVA6 controller wrapper for SHARC.

This wrapper preserves the local SHARC-facing contract used by the previous
external controller wrappers:
- read k/t/x/w from the simulation directory
- send one TCP request per control step
- write u/metadata back to SHARC

The transport target changes from the previous GVSoC-specific backend to a
generic CVA6 TCP backend, but SHARC should not need any change.
"""

import json
import os
import socket
import sys
import time
from typing import Any, Dict, List, Tuple, Union


if len(sys.argv) > 1:
    SIMULATION_DIR = os.path.abspath(sys.argv[1])
else:
    SIMULATION_DIR = os.getcwd()


U_OUT = os.path.join(SIMULATION_DIR, "u_c++_to_py")
METADATA_OUT = os.path.join(SIMULATION_DIR, "metadata_c++_to_py")
STATUS_IN = os.path.join(SIMULATION_DIR, "status_py_to_c++")
K_IN = os.path.join(SIMULATION_DIR, "k_py_to_c++")
T_IN = os.path.join(SIMULATION_DIR, "t_py_to_c++")
X_IN = os.path.join(SIMULATION_DIR, "x_py_to_c++")
W_IN = os.path.join(SIMULATION_DIR, "w_py_to_c++")
T_DELAY_IN = os.path.join(SIMULATION_DIR, "t_delay_py_to_c++")
TRACE_FILE = os.path.join(SIMULATION_DIR, "cva6_wrapper_trace.ndjson")


CVA6_TRANSPORT = os.environ.get("CVA6_TRANSPORT", "tcp").strip().lower()
CVA6_HOST = os.environ.get("CVA6_HOST", "127.0.0.1")
CVA6_PORT = int(os.environ.get("CVA6_PORT", "5001"))
try:
    CVA6_SOCKET_TIMEOUT_S = float(os.environ.get("CVA6_SOCKET_TIMEOUT_S", "60"))
except ValueError:
    CVA6_SOCKET_TIMEOUT_S = 60.0

OFFICIAL_CVA6_MODE = os.environ.get("SHARC_CVA6_OFFICIAL_MODE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class CVA6TCPClient:
    """Minimal newline-delimited JSON TCP client."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self) -> None:
        print(f"[CVA6 Wrapper] Connecting to backend at {self.host}:{self.port}", file=sys.stderr)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(CVA6_SOCKET_TIMEOUT_S)

        for attempt in range(5):
            try:
                self.sock.connect((self.host, self.port))
                print("[CVA6 Wrapper] Connected", file=sys.stderr)
                return
            except Exception as exc:
                print(f"[CVA6 Wrapper] Attempt {attempt + 1}/5 failed: {exc}", file=sys.stderr)
                if attempt == 4:
                    raise
                time.sleep(2)

    def send_request(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        if self.sock is None:
            raise RuntimeError("TCP client is not connected")
        payload = json.dumps(request_dict, separators=(",", ":")) + "\n"
        self.sock.sendall(payload.encode("utf-8"))

        data = b""
        while b"\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed by server")
            data += chunk
        line = data.split(b"\n", 1)[0]
        return json.loads(line.decode("utf-8"))

    def close(self, send_shutdown: bool = False) -> None:
        if self.sock is None:
            return
        if send_shutdown:
            try:
                self.sock.sendall((json.dumps({"type": "shutdown"}) + "\n").encode("utf-8"))
            except Exception:
                pass
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = None


class PipeController:
    """Pipe I/O adapter that preserves the SHARC-facing protocol."""

    def __init__(self):
        self.u_writer = None
        self.metadata_writer = None
        self.k_reader = None
        self.t_reader = None
        self.x_reader = None
        self.w_reader = None
        self.t_delay_reader = None

    def open_pipes(self) -> None:
        self.u_writer = open(U_OUT, "w", buffering=1)
        self.metadata_writer = open(METADATA_OUT, "w", buffering=1)
        self.k_reader = open(K_IN, "r")
        self.t_reader = open(T_IN, "r")
        self.x_reader = open(X_IN, "r")
        self.w_reader = open(W_IN, "r")
        self.t_delay_reader = open(T_DELAY_IN, "r")

    def _read_line(self, reader, name: str) -> str:
        line = reader.readline()
        if line == "":
            raise EOFError(f"EOF on {name}")
        line = line.strip()
        if line == "END OF PIPE":
            raise EOFError(f"END OF PIPE on {name}")
        return line

    def read_int(self, reader, name: str) -> int:
        return int(self._read_line(reader, name))

    def read_float(self, reader, name: str) -> float:
        return float(self._read_line(reader, name))

    def read_vector(self, reader, name: str) -> List[float]:
        line = self._read_line(reader, name)
        line = line.replace("[", "").replace("]", "").strip()
        if line == "":
            return []
        return [float(item.strip()) for item in line.split(",") if item.strip() != ""]

    def read_status(self) -> str:
        if not os.path.exists(STATUS_IN):
            return "RUNNING"
        try:
            with open(STATUS_IN, "r", encoding="utf-8") as fh:
                return fh.read().strip()
        except Exception:
            return "RUNNING"

    def write_vector(self, writer, vec: List[float], name: str) -> None:
        _ = name
        payload = "[" + ", ".join(f"{v:.12g}" for v in vec) + "]"
        writer.write(payload + "\n")
        writer.flush()

    def write_json(self, writer, data: Dict[str, Any], name: str) -> None:
        _ = name
        writer.write(json.dumps(data, separators=(",", ":")) + "\n")
        writer.flush()

    def close_pipes(self) -> None:
        if self.u_writer:
            try:
                self.u_writer.write("END OF PIPE\n")
                self.u_writer.flush()
            except Exception:
                pass
            try:
                self.u_writer.close()
            except Exception:
                pass
        if self.metadata_writer:
            try:
                self.metadata_writer.write("END OF PIPE\n")
                self.metadata_writer.flush()
            except Exception:
                pass
            try:
                self.metadata_writer.close()
            except Exception:
                pass
        for reader in (
            self.k_reader,
            self.t_reader,
            self.x_reader,
            self.w_reader,
            self.t_delay_reader,
        ):
            if reader:
                try:
                    reader.close()
                except Exception:
                    pass


def append_trace(path: str, record: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def validate_runtime_config() -> None:
    if OFFICIAL_CVA6_MODE and CVA6_TRANSPORT != "tcp":
        raise RuntimeError("SHARC_CVA6_OFFICIAL_MODE requires CVA6_TRANSPORT=tcp")


def build_run_snapshot_request(
    request_id: Union[str, int],
    k: int,
    t: float,
    x: List[float],
    w: List[float],
    u_prev: List[float],
) -> Dict[str, Any]:
    return {
        "type": "run_snapshot",
        "request_id": request_id,
        "k": int(k),
        "t": float(t),
        "x": [float(v) for v in x],
        "w": [float(v) for v in w],
        "u_prev": [float(v) for v in u_prev],
    }


def normalize_backend_response(response: Dict[str, Any]) -> Tuple[List[float], Dict[str, Any]]:
    if response.get("status") == "ERROR":
        raise RuntimeError(f"Backend error: {response}")

    u = response.get("u", [0.0, 100.0])
    if not isinstance(u, list) or len(u) != 2:
        raise RuntimeError(f"Invalid control vector in backend response: {response}")

    metadata = {
        "status": response.get("status", "UNKNOWN"),
        "iterations": int(response.get("iterations", 0)),
        "cost": float(response.get("cost", 0.0)),
        "solver_status": response.get("solver_status", response.get("status", "UNKNOWN")),
        "solver_status_msg": response.get("solver_status_msg", ""),
        "is_feasible": bool(response.get("is_feasible", True)),
        "constraint_error": float(response.get("constraint_error", 0.0)),
        "dual_residual": float(response.get("dual_residual", 0.0)),
        "t_delay": float(response.get("t_delay", 0.0)),
        "backend": "cva6",
    }
    if "metadata" in response and isinstance(response["metadata"], dict):
        metadata.update(response["metadata"])
    return [float(u[0]), float(u[1])], metadata


def main() -> None:
    print("[CVA6 Wrapper] Starting", file=sys.stderr)
    validate_runtime_config()

    client = None
    pipes = PipeController()
    u_prev = [0.0, 0.0]
    request_counter = 0

    try:
        client = CVA6TCPClient(CVA6_HOST, CVA6_PORT)
        client.connect()
        pipes.open_pipes()
        with open(TRACE_FILE, "w", encoding="utf-8"):
            pass

        while True:
            k = pipes.read_int(pipes.k_reader, "k")
            t = pipes.read_float(pipes.t_reader, "t")
            x = pipes.read_vector(pipes.x_reader, "x")
            w = pipes.read_vector(pipes.w_reader, "w")

            if pipes.read_status() == "FINISHED":
                break

            append_trace(
                TRACE_FILE,
                {
                    "request_id": request_counter,
                    "k": k,
                    "t": t,
                    "x": x,
                    "w": w,
                    "u_prev": u_prev,
                },
            )

            request = build_run_snapshot_request(
                request_id=request_counter,
                k=k,
                t=t,
                x=x,
                w=w,
                u_prev=u_prev,
            )
            response = client.send_request(request)
            u, metadata = normalize_backend_response(response)
            u_prev = u

            pipes.write_vector(pipes.u_writer, u, "u")
            pipes.write_json(pipes.metadata_writer, metadata, "metadata")

            # Keep SHARC unblocked even if the value is not used in this backend.
            _ = pipes.read_float(pipes.t_delay_reader, "t_delay")
            request_counter += 1

    except EOFError:
        pass
    finally:
        pipes.close_pipes()
        if client is not None:
            client.close(send_shutdown=False)


if __name__ == "__main__":
    main()
