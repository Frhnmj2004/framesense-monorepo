"""In-memory job store for 3D inference jobs.

This provides a simple, process-local queue and status tracking for 3D jobs.
It is intentionally minimal and can be replaced by an external queue later.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from schemas import Inference3DResultResponse


@dataclass
class JobEntry:
    job_id: str
    status: str  # queued | running | completed | failed
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: Optional[Inference3DResultResponse] = None
    error: Optional[str] = None


class JobStore:
    """Thread-safe in-memory store and simple FIFO queue."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobEntry] = {}
        self._queue: list[str] = []
        self._lock = threading.Lock()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            entry = self._jobs.get(job_id)
            if entry is None:
                entry = JobEntry(job_id=job_id, status="queued")
                self._jobs[job_id] = entry
            entry.status = "queued"
            entry.updated_at = time.time()
            self._queue.append(job_id)

    def get(self, job_id: str) -> Optional[JobEntry]:
        with self._lock:
            return self._jobs.get(job_id)

    def next_queued(self) -> Optional[JobEntry]:
        with self._lock:
            while self._queue:
                job_id = self._queue.pop(0)
                entry = self._jobs.get(job_id)
                if entry and entry.status == "queued":
                    entry.status = "running"
                    entry.updated_at = time.time()
                    return entry
        return None

    def set_completed(self, job_id: str, result: Inference3DResultResponse) -> None:
        with self._lock:
            entry = self._jobs.setdefault(job_id, JobEntry(job_id=job_id, status="completed"))
            entry.status = "completed"
            entry.result = result
            entry.error = None
            entry.updated_at = time.time()

    def set_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            entry = self._jobs.setdefault(job_id, JobEntry(job_id=job_id, status="failed"))
            entry.status = "failed"
            entry.error = error
            entry.updated_at = time.time()

