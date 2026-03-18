#!/usr/bin/env python3
"""
CVA6 runtime launcher.

Provides a stable backend entry point for the TCP server. The launcher keeps the
runtime interface independent from SHARC and from transport and supports:
- a deterministic mock mode for transport tests
- a real Spike-backed mode that executes the original SHARC MPC stack in CVA6
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from json import JSONDecoder
from pathlib import Path


RUNTIME_MODE = os.environ.get("CVA6_RUNTIME_MODE", "mock").strip().lower()
ROOT_DIR = Path(__file__).resolve().parent
REPO_DIR = ROOT_DIR.parent
SDK_DIR = Path(os.environ.get("CVA6_SDK_DIR", REPO_DIR / "CVA6_LINUX" / "cva6-sdk"))
SPIKE_BIN = Path(os.environ.get("CVA6_SPIKE_BIN", SDK_DIR / "install64" / "bin" / "spike"))
SPIKE_PAYLOAD = Path(os.environ.get("CVA6_SPIKE_PAYLOAD", SDK_DIR / "install64" / "spike_fw_payload.elf"))
RUNTIME_LOG_DIR = Path(os.environ.get("CVA6_RUNTIME_LOG_DIR", "/tmp/sharcbridge_cva6_runtime"))
SPIKE_TIMEOUT_S = float(os.environ.get("CVA6_SPIKE_TIMEOUT_S", "120"))
TARGET_RUNTIME_BIN = os.environ.get("CVA6_TARGET_RUNTIME_BIN", "/usr/bin/sharc_cva6_acc_runtime")
TARGET_BASE_CONFIG = os.environ.get(
    "CVA6_TARGET_BASE_CONFIG",
    "/usr/share/sharcbridge_cva6/base_config.json",
)
TARGET_TMP_DIR = os.environ.get("CVA6_TARGET_TMP_DIR", "/tmp/sharcbridge_cva6")


@dataclass
class SnapshotInput:
    request_id: str | int
    k: int
    t: float
    x: list[float]
    w: list[float]
    u_prev: list[float]


class CVA6RuntimeLauncher:
    """
    Backend launcher used by the TCP server.
    """

    def __init__(self, mode: str | None = None):
        self.mode = (mode or RUNTIME_MODE or "mock").strip().lower()
        RUNTIME_LOG_DIR.mkdir(parents=True, exist_ok=True)

    def health(self) -> dict:
        payload = {
            "status": "OK",
            "runtime_mode": self.mode,
        }
        if self.mode == "spike":
            payload.update(
                {
                    "spike_bin_exists": SPIKE_BIN.is_file(),
                    "spike_payload_exists": SPIKE_PAYLOAD.is_file(),
                    "target_runtime_bin": TARGET_RUNTIME_BIN,
                    "target_base_config": TARGET_BASE_CONFIG,
                }
            )
        return payload

    def run_snapshot(self, snap: SnapshotInput) -> dict:
        if self.mode == "mock":
            return self._run_mock_snapshot(snap)
        if self.mode == "spike":
            return self._run_spike_snapshot(snap)
        raise RuntimeError(f"Unsupported runtime mode: {self.mode}")

    def _run_mock_snapshot(self, snap: SnapshotInput) -> dict:
        t0 = time.perf_counter()

        v = float(snap.x[2]) if len(snap.x) > 2 else 0.0
        v_front = float(snap.w[0]) if len(snap.w) > 0 else v
        headway = float(snap.x[1]) if len(snap.x) > 1 else 0.0
        closing = max(0.0, v - v_front)

        accel = 0.0
        brake = 0.0
        if headway < 20.0 or closing > 1.0:
            brake = min(6507.0, 120.0 * closing + max(0.0, 25.0 - headway) * 15.0)
        else:
            accel = min(4880.0, max(0.0, 15.0 - v) * 90.0)

        t_delay = time.perf_counter() - t0
        return {
            "status": "SUCCESS",
            "request_id": snap.request_id,
            "k": int(snap.k),
            "u": [float(accel), float(brake)],
            "iterations": 1,
            "cost": float(-(headway * 10.0) - closing),
            "solver_status": "SUCCESS",
            "solver_status_msg": "",
            "is_feasible": True,
            "constraint_error": 0.0,
            "dual_residual": 0.0,
            "t_delay": t_delay,
            "metadata": {
                "backend_mode": self.mode,
                "launcher": "cva6_runtime_launcher",
            },
        }

    def _run_spike_snapshot(self, snap: SnapshotInput) -> dict:
        if not SPIKE_BIN.is_file():
            raise RuntimeError(f"Spike binary not found: {SPIKE_BIN}")
        if not SPIKE_PAYLOAD.is_file():
            raise RuntimeError(f"Spike payload not found: {SPIKE_PAYLOAD}")

        request_tag = _sanitize_tag(snap.request_id)
        guest_snapshot_path = f"{TARGET_TMP_DIR}/snapshot_{request_tag}.json"
        snapshot_payload = {
            "snapshot_id": str(snap.request_id),
            "k": int(snap.k),
            "t": float(snap.t),
            "x": [float(v) for v in snap.x],
            "w": [float(v) for v in snap.w],
            "u_prev": [float(v) for v in snap.u_prev],
        }
        spike_input = _build_spike_input(snapshot_payload, guest_snapshot_path)
        log_path = RUNTIME_LOG_DIR / f"{request_tag}.log"

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(SPIKE_BIN), str(SPIKE_PAYLOAD)],
                input=spike_input,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=SPIKE_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            log_path.write_text(output, encoding="utf-8")
            raise RuntimeError(f"Spike timeout after {SPIKE_TIMEOUT_S:.1f}s (log: {log_path})") from exc

        t_delay = time.perf_counter() - t0
        output = proc.stdout or ""
        log_path.write_text(output, encoding="utf-8")

        if proc.returncode != 0:
            raise RuntimeError(f"Spike exited with code {proc.returncode} (log: {log_path})")

        runtime_json = _extract_runtime_json(output)
        if runtime_json is None:
            raise RuntimeError(f"Could not extract runtime JSON from Spike output (log: {log_path})")

        metadata = runtime_json.get("metadata", {})
        return {
            "status": str(metadata.get("status", "SUCCESS")),
            "request_id": snap.request_id,
            "k": int(runtime_json.get("k", snap.k)),
            "u": [float(runtime_json["u"][0]), float(runtime_json["u"][1])],
            "iterations": int(metadata.get("iterations", 0)),
            "cost": float(metadata.get("cost", 0.0)),
            "solver_status": str(metadata.get("solver_status", "")),
            "solver_status_msg": str(metadata.get("solver_status_msg", "")),
            "is_feasible": bool(metadata.get("is_feasible", False)),
            "constraint_error": float(metadata.get("constraint_error", 0.0)),
            "dual_residual": float(metadata.get("dual_residual", 0.0)),
            "t_delay": t_delay,
            "metadata": {
                "backend_mode": self.mode,
                "launcher": "cva6_runtime_launcher",
                "log_path": str(log_path),
                "runtime_metadata": metadata,
            },
        }


def _sanitize_tag(value: str | int) -> str:
    text = str(value)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:80] or "snapshot"


def _build_spike_input(snapshot_payload: dict, guest_snapshot_path: str) -> str:
    snapshot_json = json.dumps(snapshot_payload, separators=(",", ":"))
    return (
        f"mkdir -p {TARGET_TMP_DIR}\n"
        f"cat > {guest_snapshot_path} <<'JSON'\n"
        f"{snapshot_json}\n"
        "JSON\n"
        f"{TARGET_RUNTIME_BIN} {TARGET_BASE_CONFIG} {guest_snapshot_path}\n"
        "poweroff -f\n"
    )


def _extract_runtime_json(text: str) -> dict | None:
    decoder = JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if "u" in obj and "metadata" in obj and "snapshot_id" in obj:
            return obj
    return None
