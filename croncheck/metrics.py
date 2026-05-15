"""Simple in-memory metrics collector for croncheck."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


@dataclass
class JobMetrics:
    """Per-job execution metrics."""
    job_name: str
    total_checkins: int = 0
    missed_runs: int = 0
    last_checkin_ts: Optional[float] = None
    last_alert_ts: Optional[float] = None

    @property
    def last_checkin_age_seconds(self) -> Optional[float]:
        if self.last_checkin_ts is None:
            return None
        return time.time() - self.last_checkin_ts


class MetricsCollector:
    """Thread-safe collector for cron job metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: Dict[str, JobMetrics] = {}

    def _get_or_create(self, job_name: str) -> JobMetrics:
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetrics(job_name=job_name)
        return self._jobs[job_name]

    def record_checkin(self, job_name: str) -> None:
        with self._lock:
            m = self._get_or_create(job_name)
            m.total_checkins += 1
            m.last_checkin_ts = time.time()

    def record_missed(self, job_name: str) -> None:
        with self._lock:
            m = self._get_or_create(job_name)
            m.missed_runs += 1
            m.last_alert_ts = time.time()

    def get(self, job_name: str) -> Optional[JobMetrics]:
        with self._lock:
            return self._jobs.get(job_name)

    def all(self) -> Dict[str, JobMetrics]:
        with self._lock:
            return dict(self._jobs)

    def reset(self, job_name: str) -> None:
        with self._lock:
            self._jobs.pop(job_name, None)

    def summary(self) -> Dict[str, dict]:
        with self._lock:
            return {
                name: {
                    "total_checkins": m.total_checkins,
                    "missed_runs": m.missed_runs,
                    "last_checkin_age_seconds": m.last_checkin_age_seconds,
                }
                for name, m in self._jobs.items()
            }
