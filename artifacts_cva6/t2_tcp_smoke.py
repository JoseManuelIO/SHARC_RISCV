#!/usr/bin/env python3
import json
import socket
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER = REPO_ROOT / "SHARCBRIDGE_CVA6" / "cva6_tcp_server.py"
OUT_JSON = REPO_ROOT / "artifacts_cva6" / "t2_tcp_roundtrip.json"
OUT_LOG = REPO_ROOT / "artifacts_cva6" / "t2_tcp_health.log"
HOST = "127.0.0.1"
PORT = 5001


def send(payload):
    with socket.create_connection((HOST, PORT), timeout=5.0) as sock:
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))


proc = subprocess.Popen(
    [sys.executable, str(SERVER)],
    cwd=str(REPO_ROOT),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
)

try:
    time.sleep(1.0)
    health = send({"type": "health", "request_id": "health-1"})
    result = send(
        {
            "type": "run_snapshot",
            "request_id": "snap-1",
            "k": 3,
            "t": 0.6,
            "x": [1.0, 45.0, 14.5],
            "w": [13.0, 1.0],
            "u_prev": [0.0, 0.0],
        }
    )
    send({"type": "shutdown", "request_id": "shutdown-1"})
    proc.wait(timeout=5.0)

    OUT_JSON.write_text(
        json.dumps(
            {
                "health": health,
                "run_snapshot": result,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    OUT_LOG.write_text("T2 TCP smoke PASS\n", encoding="utf-8")
except Exception:
    proc.kill()
    raise
