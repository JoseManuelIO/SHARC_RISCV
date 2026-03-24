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
import selectors
import subprocess
import threading
import time
import hashlib
from base64 import b64encode
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
SPIKE_BOOT_TIMEOUT_S = float(os.environ.get("CVA6_SPIKE_BOOT_TIMEOUT_S", "30"))
SPIKE_READY_TIMEOUT_S = float(os.environ.get("CVA6_SPIKE_READY_TIMEOUT_S", "60"))
SPIKE_BOOT_IDLE_S = float(os.environ.get("CVA6_SPIKE_BOOT_IDLE_S", "10.0"))
TARGET_RUNTIME_BIN = os.environ.get("CVA6_TARGET_RUNTIME_BIN", "/usr/bin/sharc_cva6_acc_runtime")
TARGET_BASE_CONFIG = os.environ.get(
    "CVA6_TARGET_BASE_CONFIG",
    "/usr/share/sharcbridge_cva6/base_config.json",
)
TARGET_TMP_DIR = os.environ.get("CVA6_TARGET_TMP_DIR", "/tmp/sharcbridge_cva6")
STAGED_RUNTIME_BIN = os.environ.get("CVA6_STAGED_RUNTIME_BIN", f"{TARGET_TMP_DIR}/sharc_cva6_acc_runtime")
STAGED_BASE_CONFIG = os.environ.get("CVA6_STAGED_BASE_CONFIG", f"{TARGET_TMP_DIR}/base_config.json")
HOST_RUNTIME_BIN = Path(
    os.environ.get(
        "CVA6_HOST_RUNTIME_BIN",
        SDK_DIR / "buildroot" / "output" / "target" / "usr" / "bin" / "sharc_cva6_acc_runtime",
    )
)
HOST_BASE_CONFIG = Path(
    os.environ.get(
        "CVA6_HOST_BASE_CONFIG",
        SDK_DIR / "buildroot" / "output" / "target" / "usr" / "share" / "sharcbridge_cva6" / "base_config.json",
    )
)
SHELL_PROMPT = os.environ.get("CVA6_SPIKE_SHELL_PROMPT", "# ")
BOOT_READY_MARKERS = [
    SHELL_PROMPT,
    "Starting sshd: OK",
    "NFS preparation skipped, OK",
]
BOOT_PROGRESS_MARKERS = BOOT_READY_MARKERS + [
    "Starting rpcbind: OK",
    "Running sysctl: OK",
    "Run /init as init process",
]
BOOT_LATE_PROGRESS_MARKERS = ["Starting sshd: "] + BOOT_READY_MARKERS


def _load_host_asset_b64(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing host asset required for guest staging: {path}")
    return b64encode(path.read_bytes()).decode("ascii")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


HOST_RUNTIME_BIN_B64 = _load_host_asset_b64(HOST_RUNTIME_BIN)
HOST_BASE_CONFIG_B64 = _load_host_asset_b64(HOST_BASE_CONFIG)
HOST_RUNTIME_BIN_SHA256 = _sha256_file(HOST_RUNTIME_BIN)
HOST_BASE_CONFIG_SHA256 = _sha256_file(HOST_BASE_CONFIG)
HOST_RUNTIME_BIN_SIZE = HOST_RUNTIME_BIN.stat().st_size
HOST_BASE_CONFIG_SIZE = HOST_BASE_CONFIG.stat().st_size


@dataclass
class SnapshotInput:
    request_id: str | int
    k: int
    t: float
    x: list[float]
    w: list[float]
    u_prev: list[float]


class PersistentSpikeSession:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.selector: selectors.BaseSelector | None = None
        self.lock = threading.Lock()
        self.session_log_path = RUNTIME_LOG_DIR / "persistent_session.log"
        self.session_log = None
        self._guest_assets_ready = False

    def start(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            return

        self.close()
        self.session_log = self.session_log_path.open("a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [str(SPIKE_BIN), str(SPIKE_PAYLOAD)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)

        _wait_for_boot_ready(self._read_until, self._read_until_idle)
        _ensure_interactive_shell_ready(self.proc, self._read_until)
        self._ensure_guest_assets()

    def run_snapshot(self, snap: SnapshotInput) -> tuple[dict, str]:
        with self.lock:
            self.start()
            assert self.proc is not None
            assert self.proc.stdin is not None

            request_tag = _sanitize_tag(snap.request_id)
            guest_snapshot_path = f"{TARGET_TMP_DIR}/snapshot_{request_tag}.json"
            begin_marker = f"__SHARCBRIDGE_BEGIN_{request_tag}__"
            end_marker = f"__SHARCBRIDGE_END_{request_tag}__"
            snapshot_payload = {
                "snapshot_id": str(snap.request_id),
                "k": int(snap.k),
                "t": float(snap.t),
                "x": [float(v) for v in snap.x],
                "w": [float(v) for v in snap.w],
                "u_prev": [float(v) for v in snap.u_prev],
            }
            command = _build_spike_command(
                snapshot_payload=snapshot_payload,
                guest_snapshot_path=guest_snapshot_path,
                begin_marker=begin_marker,
                end_marker=end_marker,
            )

            self.proc.stdin.write(command.encode("utf-8"))
            self.proc.stdin.flush()

            command_text = self._read_until([end_marker], SPIKE_TIMEOUT_S)
            payload_text = _extract_between_markers(command_text, begin_marker, end_marker)
            if payload_text is None:
                raise RuntimeError(f"Could not isolate runtime output for request {request_tag}")

            runtime_json = _extract_runtime_json(payload_text)
            if runtime_json is None:
                raise RuntimeError(f"Could not extract runtime JSON from persistent Spike output for request {request_tag}")
            return runtime_json, payload_text

    def _ensure_guest_assets(self) -> None:
        if self._guest_assets_ready:
            return

        assert self.proc is not None
        assert self.proc.stdin is not None

        stage_begin = "__SHARCBRIDGE_STAGE_BEGIN__"
        stage_end = "__SHARCBRIDGE_STAGE_END__"
        self.proc.stdin.write(_build_guest_asset_stage_command(stage_begin, stage_end).encode("utf-8"))
        self.proc.stdin.flush()
        stage_text = self._read_until([stage_end], SPIKE_TIMEOUT_S)
        if "STAGE_RUNTIME_READY=1" not in stage_text:
            raise RuntimeError("Guest runtime staging did not produce a usable runtime binary")
        if "STAGE_CONFIG_READY=1" not in stage_text:
            raise RuntimeError("Guest runtime staging did not produce a usable base config")
        _validate_optional_stage_hash(
            stage_text,
            marker_name="STAGE_RUNTIME_SHA",
            expected_hash=HOST_RUNTIME_BIN_SHA256,
            error_message="Guest runtime staging hash did not match the host runtime binary",
        )
        _validate_optional_stage_hash(
            stage_text,
            marker_name="STAGE_CONFIG_SHA",
            expected_hash=HOST_BASE_CONFIG_SHA256,
            error_message="Guest config staging hash did not match the host config",
        )
        self._guest_assets_ready = True

    def _read_until(self, markers: list[str], timeout_s: float) -> str:
        if self.proc is None or self.selector is None:
            raise RuntimeError("Persistent Spike session is not started")

        deadline = time.time() + timeout_s
        chunks: list[str] = []
        while time.time() < deadline:
            events = self.selector.select(timeout=0.2)
            if not events:
                continue
            for key, _ in events:
                chunk = key.fileobj.read(4096)
                if not chunk:
                    self.close()
                    raise RuntimeError("Persistent Spike session closed unexpectedly")
                text = chunk.decode("utf-8", errors="ignore")
                if self.session_log is not None:
                    self.session_log.write(text)
                    self.session_log.flush()
                chunks.append(text)
                joined = "".join(chunks)
                for marker in markers:
                    if marker in joined:
                        return joined
        raise RuntimeError(f"Timeout waiting for markers {markers}")

    def _read_until_idle(self, idle_s: float, timeout_s: float, stop_markers: list[str] | None = None) -> str:
        if self.proc is None or self.selector is None:
            raise RuntimeError("Persistent Spike session is not started")

        deadline = time.time() + timeout_s
        chunks: list[str] = []
        last_output_ts = time.time()
        while time.time() < deadline:
            events = self.selector.select(timeout=0.2)
            if not events:
                if self.proc.poll() is not None:
                    self.close()
                    raise RuntimeError("Persistent Spike session closed unexpectedly")
                if time.time() - last_output_ts >= idle_s:
                    return "".join(chunks)
                continue
            for key, _ in events:
                chunk = key.fileobj.read(4096)
                if not chunk:
                    if self.proc.poll() is not None:
                        self.close()
                        raise RuntimeError("Persistent Spike session closed unexpectedly")
                    continue
                text = chunk.decode("utf-8", errors="ignore")
                if self.session_log is not None:
                    self.session_log.write(text)
                    self.session_log.flush()
                chunks.append(text)
                last_output_ts = time.time()
                joined = "".join(chunks)
                if stop_markers:
                    for marker in stop_markers:
                        if marker in joined:
                            return joined
        raise RuntimeError(f"Timeout waiting for idle window or markers {stop_markers}")

    def close(self) -> None:
        if self.selector is not None:
            try:
                self.selector.close()
            except Exception:
                pass
            self.selector = None

        if self.proc is not None:
            try:
                if self.proc.poll() is None and self.proc.stdin is not None:
                    try:
                        self.proc.stdin.write(b"poweroff -f\n")
                        self.proc.stdin.flush()
                    except Exception:
                        pass
                    time.sleep(0.2)
                    if self.proc.poll() is None:
                        self.proc.kill()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
            self._guest_assets_ready = False

        if self.session_log is not None:
            try:
                self.session_log.close()
            except Exception:
                pass
            self.session_log = None


class CVA6RuntimeLauncher:
    """
    Backend launcher used by the TCP server.
    """

    def __init__(self, mode: str | None = None):
        self.mode = (mode or RUNTIME_MODE or "mock").strip().lower()
        RUNTIME_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._persistent_session = PersistentSpikeSession() if self.mode == "spike_persistent" else None

    def health(self) -> dict:
        payload = {
            "status": "OK",
            "runtime_mode": self.mode,
        }
        if self.mode in {"spike", "spike_persistent"}:
            payload.update(
                {
                    "sdk_dir": str(SDK_DIR.resolve()),
                    "spike_bin": str(SPIKE_BIN.resolve(strict=False)),
                    "spike_payload": str(SPIKE_PAYLOAD.resolve(strict=False)),
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
        if self.mode == "spike_persistent":
            return self._run_spike_persistent_snapshot(snap)
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
        begin_marker = "__SHARCBRIDGE_BEGIN_ONESHOT__"
        end_marker = "__SHARCBRIDGE_END_ONESHOT__"
        command = _build_spike_command(
            snapshot_payload=snapshot_payload,
            guest_snapshot_path=guest_snapshot_path,
            begin_marker=begin_marker,
            end_marker=end_marker,
        ) + "poweroff -f\n"
        log_path = RUNTIME_LOG_DIR / f"{request_tag}.log"

        t0 = time.perf_counter()
        output = _run_spike_oneshot_command(command, [end_marker], log_path)
        t_delay = time.perf_counter() - t0

        payload_text = _extract_between_markers(output, begin_marker, end_marker)
        if payload_text is None:
            raise RuntimeError(f"Could not isolate runtime output for oneshot request {request_tag} (log: {log_path})")

        runtime_json = _extract_runtime_json(payload_text)
        if runtime_json is None:
            raise RuntimeError(f"Could not extract runtime JSON from Spike oneshot output (log: {log_path})")

        return self._normalize_runtime_output(runtime_json, snap, t_delay, log_path)

    def _run_spike_persistent_snapshot(self, snap: SnapshotInput) -> dict:
        if self._persistent_session is None:
            raise RuntimeError("Persistent Spike session is not initialized")
        t0 = time.perf_counter()
        runtime_json, payload_text = self._persistent_session.run_snapshot(snap)
        t_delay = time.perf_counter() - t0
        request_tag = _sanitize_tag(snap.request_id)
        log_path = RUNTIME_LOG_DIR / f"persistent_{request_tag}.log"
        log_path.write_text(payload_text, encoding="utf-8")
        return self._normalize_runtime_output(runtime_json, snap, t_delay, log_path)

    def _normalize_runtime_output(self, runtime_json: dict, snap: SnapshotInput, t_delay: float, log_path: Path) -> dict:
        metadata = runtime_json.get("metadata", {})
        return {
            "status": str(metadata.get("status", "SUCCESS")),
            "request_id": snap.request_id,
            "k": int(runtime_json.get("k", snap.k)),
            "u": [float(runtime_json["u"][0]), float(runtime_json["u"][1])],
            "iterations": int(metadata.get("iterations", 0)),
            "cost": float(metadata.get("cost", 0.0)),
            "cycles": int(metadata.get("cycles", 0)),
            "instret": int(metadata.get("instret", 0)),
            "cpi": float(metadata.get("cpi", 0.0)),
            "ipc": float(metadata.get("ipc", 0.0)),
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

    def close(self) -> None:
        if self._persistent_session is not None:
            self._persistent_session.close()


def _sanitize_tag(value: str | int) -> str:
    text = str(value)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:80] or "snapshot"


def _build_spike_command(snapshot_payload: dict, guest_snapshot_path: str, begin_marker: str, end_marker: str) -> str:
    snapshot_json = json.dumps(snapshot_payload, separators=(",", ":"))
    return (
        f"mkdir -p {TARGET_TMP_DIR}\n"
        f"printf '%s\\n' '{snapshot_json}' > {guest_snapshot_path}\n"
        f'RUNTIME_BIN="{TARGET_RUNTIME_BIN}"\n'
        f'[ -x "$RUNTIME_BIN" ] || RUNTIME_BIN="{STAGED_RUNTIME_BIN}"\n'
        f'BASE_CONFIG="{TARGET_BASE_CONFIG}"\n'
        f'[ -e "$BASE_CONFIG" ] || BASE_CONFIG="{STAGED_BASE_CONFIG}"\n'
        f"echo {begin_marker}\n"
        f'"$RUNTIME_BIN" "$BASE_CONFIG" {guest_snapshot_path}\n'
        f"echo {end_marker}\n"
    )


def _build_spike_input(snapshot_payload: dict, guest_snapshot_path: str) -> str:
    return _build_spike_command(
        snapshot_payload=snapshot_payload,
        guest_snapshot_path=guest_snapshot_path,
        begin_marker="__SHARCBRIDGE_BEGIN_ONESHOT__",
        end_marker="__SHARCBRIDGE_END_ONESHOT__",
    ) + "poweroff -f\n"


def _validate_optional_stage_hash(stage_text: str, marker_name: str, expected_hash: str, error_message: str) -> None:
    marker = f"{marker_name}="
    if marker not in stage_text:
        return
    if f"{marker}{expected_hash}" not in stage_text:
        raise RuntimeError(error_message)


def _run_spike_oneshot_command(command: str, end_markers: list[str], log_path: Path) -> str:
    proc = subprocess.Popen(
        [str(SPIKE_BIN), str(SPIKE_PAYLOAD)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    selector = selectors.DefaultSelector()
    output_chunks: list[str] = []

    def _read_until(markers: list[str], timeout_s: float) -> str:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            events = selector.select(timeout=0.2)
            if not events:
                if proc.poll() is not None:
                    raise RuntimeError(f"Spike exited with code {proc.returncode} before markers {markers}")
                continue
            for key, _ in events:
                chunk = key.fileobj.read(4096)
                if not chunk:
                    if proc.poll() is not None:
                        raise RuntimeError(f"Spike exited with code {proc.returncode} before markers {markers}")
                    continue
                text = chunk.decode("utf-8", errors="ignore")
                output_chunks.append(text)
                joined = "".join(output_chunks)
                for marker in markers:
                    if marker in joined:
                        return joined
        raise RuntimeError(f"Timeout waiting for markers {markers}")

    def _read_until_idle(idle_s: float, timeout_s: float, stop_markers: list[str] | None = None) -> str:
        deadline = time.time() + timeout_s
        last_output_ts = time.time()
        while time.time() < deadline:
            events = selector.select(timeout=0.2)
            if not events:
                if proc.poll() is not None:
                    raise RuntimeError(f"Spike exited with code {proc.returncode} before idle window or markers {stop_markers}")
                if time.time() - last_output_ts >= idle_s:
                    return "".join(output_chunks)
                continue
            for key, _ in events:
                chunk = key.fileobj.read(4096)
                if not chunk:
                    if proc.poll() is not None:
                        raise RuntimeError(f"Spike exited with code {proc.returncode} before idle window or markers {stop_markers}")
                    continue
                text = chunk.decode("utf-8", errors="ignore")
                output_chunks.append(text)
                last_output_ts = time.time()
                joined = "".join(output_chunks)
                if stop_markers:
                    for marker in stop_markers:
                        if marker in joined:
                            return joined
        raise RuntimeError(f"Timeout waiting for idle window or markers {stop_markers}")

    try:
        if proc.stdout is None or proc.stdin is None:
            raise RuntimeError("Failed to open Spike stdio streams")
        selector.register(proc.stdout, selectors.EVENT_READ)

        _wait_for_boot_ready(_read_until, _read_until_idle)
        _ensure_interactive_shell_ready(proc, _read_until)
        proc.stdin.write(
            _build_guest_asset_stage_command(
                "__SHARCBRIDGE_STAGE_BEGIN__",
                "__SHARCBRIDGE_STAGE_END__",
            ).encode("utf-8")
        )
        proc.stdin.flush()
        _read_until(["__SHARCBRIDGE_STAGE_END__"], SPIKE_TIMEOUT_S)
        proc.stdin.write(command.encode("utf-8"))
        proc.stdin.flush()
        output = _read_until(end_markers, SPIKE_TIMEOUT_S)
        return output
    finally:
        try:
            log_path.write_text("".join(output_chunks), encoding="utf-8")
        except Exception:
            pass
        try:
            selector.close()
        except Exception:
            pass
        try:
            if proc.poll() is None and proc.stdin is not None:
                try:
                    proc.stdin.write(b"poweroff -f\n")
                    proc.stdin.flush()
                except Exception:
                    pass
                time.sleep(0.2)
                if proc.poll() is None:
                    proc.kill()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


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


def _extract_between_markers(text: str, begin_marker: str, end_marker: str) -> str | None:
    begin = text.find(begin_marker)
    if begin == -1:
        return None
    begin += len(begin_marker)
    end = text.find(end_marker, begin)
    if end == -1:
        return None
    return text[begin:end]


def _wait_for_boot_ready(read_until_fn, read_until_idle_fn) -> str:
    boot_text = read_until_fn(BOOT_PROGRESS_MARKERS, SPIKE_BOOT_TIMEOUT_S)
    if any(marker in boot_text for marker in BOOT_READY_MARKERS):
        return boot_text
    late_boot_text = ""
    try:
        late_boot_text = read_until_fn(BOOT_LATE_PROGRESS_MARKERS, SPIKE_READY_TIMEOUT_S)
    except RuntimeError:
        return boot_text + read_until_idle_fn(
            SPIKE_BOOT_IDLE_S,
            SPIKE_READY_TIMEOUT_S,
            BOOT_READY_MARKERS,
        )

    combined = boot_text + late_boot_text
    if any(marker in combined for marker in BOOT_READY_MARKERS):
        return combined
    return combined + read_until_idle_fn(
        SPIKE_BOOT_IDLE_S,
        SPIKE_READY_TIMEOUT_S,
        BOOT_READY_MARKERS,
    )


def _ensure_interactive_shell_ready(proc: subprocess.Popen, read_until_fn, attempts: int = 3) -> None:
    if proc.stdin is None:
        raise RuntimeError("Spike stdin is not available to establish shell readiness")

    for attempt in range(attempts):
        ready_marker = f"__SHARCBRIDGE_SHELL_READY_{attempt}__"
        proc.stdin.write(b"\n")
        proc.stdin.flush()
        try:
            read_until_fn([SHELL_PROMPT], 10)
        except RuntimeError:
            pass
        proc.stdin.write(f"echo {ready_marker}\n".encode("utf-8"))
        proc.stdin.flush()
        try:
            read_until_fn([ready_marker], 15)
            return
        except RuntimeError:
            continue
    raise RuntimeError("Could not establish an interactive guest shell before staging")


def _build_guest_asset_stage_command(begin_marker: str, end_marker: str) -> str:
    return (
        f"mkdir -p {TARGET_TMP_DIR}\n"
        f"echo {begin_marker}\n"
        "stty -echo 2>/dev/null || true\n"
        f'if [ ! -x "{TARGET_RUNTIME_BIN}" ] && [ ! -x "{STAGED_RUNTIME_BIN}" ]; then\n'
        f'RUNTIME_B64="{STAGED_RUNTIME_BIN}.b64"\n'
        f'RUNTIME_TMP="{STAGED_RUNTIME_BIN}.tmp"\n'
        f'rm -f "$RUNTIME_B64" "$RUNTIME_TMP"\n'
        f"{_build_base64_heredoc_commands(HOST_RUNTIME_BIN_B64, '$RUNTIME_B64', 'SHARCBRIDGE_RUNTIME_B64')}"
        'if base64 -d "$RUNTIME_B64" > "$RUNTIME_TMP"; then\n'
        f'RUNTIME_SHA="$(sha256sum "$RUNTIME_TMP" | awk \'{{print $1}}\')"\n'
        f'RUNTIME_SIZE="$(wc -c < "$RUNTIME_TMP" | tr -d \' \')"\n'
        'echo "STAGE_RUNTIME_SHA=$RUNTIME_SHA"\n'
        'echo "STAGE_RUNTIME_SIZE=$RUNTIME_SIZE"\n'
        f'if [ "$RUNTIME_SHA" = "{HOST_RUNTIME_BIN_SHA256}" ] && [ "$RUNTIME_SIZE" = "{HOST_RUNTIME_BIN_SIZE}" ]; then\n'
        f'chmod +x "$RUNTIME_TMP"\n'
        f'mv "$RUNTIME_TMP" "{STAGED_RUNTIME_BIN}"\n'
        "else\n"
        'rm -f "$RUNTIME_TMP"\n'
        "fi\n"
        "fi\n"
        'rm -f "$RUNTIME_B64" "$RUNTIME_TMP"\n'
        "fi\n"
        f'if [ ! -e "{TARGET_BASE_CONFIG}" ] && [ ! -e "{STAGED_BASE_CONFIG}" ]; then\n'
        f'CONFIG_B64="{STAGED_BASE_CONFIG}.b64"\n'
        f'CONFIG_TMP="{STAGED_BASE_CONFIG}.tmp"\n'
        f'rm -f "$CONFIG_B64" "$CONFIG_TMP"\n'
        f"{_build_base64_heredoc_commands(HOST_BASE_CONFIG_B64, '$CONFIG_B64', 'SHARCBRIDGE_CONFIG_B64')}"
        'if base64 -d "$CONFIG_B64" > "$CONFIG_TMP"; then\n'
        f'CONFIG_SHA="$(sha256sum "$CONFIG_TMP" | awk \'{{print $1}}\')"\n'
        f'CONFIG_SIZE="$(wc -c < "$CONFIG_TMP" | tr -d \' \')"\n'
        'echo "STAGE_CONFIG_SHA=$CONFIG_SHA"\n'
        'echo "STAGE_CONFIG_SIZE=$CONFIG_SIZE"\n'
        f'if [ "$CONFIG_SHA" = "{HOST_BASE_CONFIG_SHA256}" ] && [ "$CONFIG_SIZE" = "{HOST_BASE_CONFIG_SIZE}" ]; then\n'
        f'mv "$CONFIG_TMP" "{STAGED_BASE_CONFIG}"\n'
        "else\n"
        'rm -f "$CONFIG_TMP"\n'
        "fi\n"
        "fi\n"
        'rm -f "$CONFIG_B64" "$CONFIG_TMP"\n'
        "fi\n"
        f'if [ -x "{TARGET_RUNTIME_BIN}" ] || [ -x "{STAGED_RUNTIME_BIN}" ]; then echo STAGE_RUNTIME_READY=1; else echo STAGE_RUNTIME_READY=0; fi\n'
        f'if [ -e "{TARGET_BASE_CONFIG}" ] || [ -e "{STAGED_BASE_CONFIG}" ]; then echo STAGE_CONFIG_READY=1; else echo STAGE_CONFIG_READY=0; fi\n'
        "stty echo 2>/dev/null || true\n"
        f"echo {end_marker}\n"
    )


def _build_base64_heredoc_commands(
    payload_b64: str,
    guest_path_expr: str,
    heredoc_tag: str,
    chunk_size: int = 65536,
) -> str:
    lines = [f': > {guest_path_expr}']
    for idx in range(0, len(payload_b64), chunk_size):
        chunk = payload_b64[idx : idx + chunk_size]
        marker = f"{heredoc_tag}_{idx // chunk_size}"
        wrapped = "\n".join(
            chunk[line_start : line_start + 120] for line_start in range(0, len(chunk), 120)
        )
        lines.append(f"cat >> {guest_path_expr} <<'{marker}'")
        lines.append(wrapped)
        lines.append(marker)
    return "\n".join(lines) + "\n"
