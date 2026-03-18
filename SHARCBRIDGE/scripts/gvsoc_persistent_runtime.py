#!/usr/bin/env python3
"""
Persistent runtime pool for GVSoC/PULP offload.

T3 goals covered:
- persistent worker lifecycle (start once, reuse many requests)
- round-robin worker pool scheduling
- watchdog-style recovery + bounded retry after worker failures
"""

from __future__ import annotations

import threading
from typing import Callable


ComputeFn = Callable[[int, float, list, list, list | None], dict]
GenericComputeFn = Callable[[dict, dict | None], dict]


class WorkerExecutionError(RuntimeError):
    """Raised when a worker fails while executing a request."""

    def __init__(self, worker_id: int, cause: Exception):
        super().__init__(f"worker {worker_id} execution failed: {cause}")
        self.worker_id = worker_id
        self.cause = cause


class PersistentWorker:
    """Single persistent worker abstraction."""

    def __init__(self, worker_id: int, compute_fn: ComputeFn):
        self.worker_id = worker_id
        self._compute_fn = compute_fn
        self._lock = threading.Lock()
        self._alive = False
        self.start_count = 0
        self.restart_count = 0
        self.request_count = 0

    def _start_locked(self) -> None:
        self._alive = True
        self.start_count += 1

    def _restart_locked(self) -> None:
        self.restart_count += 1
        self._start_locked()

    def kill(self) -> None:
        """Simulate/mark worker crash; used by watchdog tests."""
        with self._lock:
            self._alive = False

    def execute(self, k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
        with self._lock:
            if not self._alive:
                if self.start_count == 0:
                    self._start_locked()
                else:
                    self._restart_locked()
            self.request_count += 1

        try:
            return self._compute_fn(k, t, x, w, u_prev)
        except Exception as exc:
            with self._lock:
                self._alive = False
            raise WorkerExecutionError(self.worker_id, exc) from exc

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "worker_id": self.worker_id,
                "alive": self._alive,
                "start_count": self.start_count,
                "spawn_count": self.start_count,
                "restart_count": self.restart_count,
                "request_count": self.request_count,
            }


class PersistentRuntimePool:
    """Round-robin pool of persistent workers with bounded retry."""

    def __init__(
        self,
        num_workers: int,
        compute_fn_factory: Callable[[int], ComputeFn],
        max_retries: int = 1,
    ):
        if num_workers <= 0:
            raise ValueError("num_workers must be > 0")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._workers = [PersistentWorker(i, compute_fn_factory(i)) for i in range(num_workers)]
        self._max_retries = max_retries
        self._rr_lock = threading.Lock()
        self._rr_index = 0

    def _next_worker(self) -> PersistentWorker:
        with self._rr_lock:
            worker = self._workers[self._rr_index]
            self._rr_index = (self._rr_index + 1) % len(self._workers)
            return worker

    def compute_mpc(self, k: int, t: float, x: list, w: list, u_prev: list | None = None) -> dict:
        last_exc: Exception | None = None
        for _ in range(self._max_retries + 1):
            worker = self._next_worker()
            try:
                return worker.execute(k, t, x, w, u_prev)
            except WorkerExecutionError as exc:
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("unreachable: no worker execution attempt made")

    def kill_worker(self, worker_id: int) -> None:
        self._workers[worker_id].kill()

    def snapshot(self) -> dict:
        workers = [w.snapshot() for w in self._workers]
        return {
            "num_workers": len(workers),
            "workers": workers,
            "total_requests": sum(w["request_count"] for w in workers),
            "total_restarts": sum(w["restart_count"] for w in workers),
            "total_starts": sum(w["start_count"] for w in workers),
            "spawn_count": sum(w["start_count"] for w in workers),
        }

    def close(self) -> None:
        for worker in self._workers:
            worker.kill()


class GenericPersistentWorker:
    """Single persistent worker for generic (non-MPC-signature) calls."""

    def __init__(self, worker_id: int, compute_fn: GenericComputeFn):
        self.worker_id = worker_id
        self._compute_fn = compute_fn
        self._lock = threading.Lock()
        self._alive = False
        self.start_count = 0
        self.restart_count = 0
        self.request_count = 0

    def _start_locked(self) -> None:
        self._alive = True
        self.start_count += 1

    def _restart_locked(self) -> None:
        self.restart_count += 1
        self._start_locked()

    def kill(self) -> None:
        with self._lock:
            self._alive = False

    def execute(self, payload: dict, settings: dict | None = None) -> dict:
        with self._lock:
            if not self._alive:
                if self.start_count == 0:
                    self._start_locked()
                else:
                    self._restart_locked()
            self.request_count += 1

        try:
            return self._compute_fn(payload, settings)
        except Exception as exc:
            with self._lock:
                self._alive = False
            raise WorkerExecutionError(self.worker_id, exc) from exc

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "worker_id": self.worker_id,
                "alive": self._alive,
                "start_count": self.start_count,
                "spawn_count": self.start_count,
                "restart_count": self.restart_count,
                "request_count": self.request_count,
            }

    def close(self) -> None:
        close_fn = getattr(self._compute_fn, "_close", None)
        if callable(close_fn):
            close_fn()
        with self._lock:
            self._alive = False


class GenericPersistentRuntimePool:
    """Round-robin pool of generic persistent workers with bounded retry."""

    def __init__(
        self,
        num_workers: int,
        compute_fn_factory: Callable[[int], GenericComputeFn],
        max_retries: int = 1,
    ):
        if num_workers <= 0:
            raise ValueError("num_workers must be > 0")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._workers = [GenericPersistentWorker(i, compute_fn_factory(i)) for i in range(num_workers)]
        self._max_retries = max_retries
        self._rr_lock = threading.Lock()
        self._rr_index = 0

    def _next_worker(self) -> GenericPersistentWorker:
        with self._rr_lock:
            worker = self._workers[self._rr_index]
            self._rr_index = (self._rr_index + 1) % len(self._workers)
            return worker

    def compute(self, payload: dict, settings: dict | None = None) -> dict:
        last_exc: Exception | None = None
        for _ in range(self._max_retries + 1):
            worker = self._next_worker()
            try:
                return worker.execute(payload, settings)
            except WorkerExecutionError as exc:
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("unreachable: no worker execution attempt made")

    def kill_worker(self, worker_id: int) -> None:
        self._workers[worker_id].kill()

    def snapshot(self) -> dict:
        workers = [w.snapshot() for w in self._workers]
        return {
            "num_workers": len(workers),
            "workers": workers,
            "total_requests": sum(w["request_count"] for w in workers),
            "total_restarts": sum(w["restart_count"] for w in workers),
            "total_starts": sum(w["start_count"] for w in workers),
            "spawn_count": sum(w["start_count"] for w in workers),
        }

    def close(self) -> None:
        for worker in self._workers:
            worker.close()
