"""Per-job alert rate limiting with sliding window counters."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class WindowEntry:
    """Tracks alert timestamps within a sliding window."""
    timestamps: Deque[float] = field(default_factory=deque)

    def prune(self, window_seconds: float) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.monotonic() - window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def record(self) -> None:
        self.timestamps.append(time.monotonic())

    def count(self) -> int:
        return len(self.timestamps)


class RateLimiter:
    """Sliding-window rate limiter for alert dispatch.

    Allows at most *max_alerts* alerts per *window_seconds* for each job.
    """

    def __init__(self, window_seconds: float = 3600.0, max_alerts: int = 5) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_alerts < 1:
            raise ValueError("max_alerts must be >= 1")
        self.window_seconds = window_seconds
        self.max_alerts = max_alerts
        self._entries: Dict[str, WindowEntry] = {}

    def _entry(self, job_name: str) -> WindowEntry:
        if job_name not in self._entries:
            self._entries[job_name] = WindowEntry()
        return self._entries[job_name]

    def is_allowed(self, job_name: str) -> bool:
        """Return True if an alert for *job_name* is within rate limits."""
        entry = self._entry(job_name)
        entry.prune(self.window_seconds)
        return entry.count() < self.max_alerts

    def record(self, job_name: str) -> None:
        """Record that an alert was sent for *job_name*."""
        self._entry(job_name).record()

    def current_count(self, job_name: str) -> int:
        """Return the number of alerts sent in the current window."""
        entry = self._entry(job_name)
        entry.prune(self.window_seconds)
        return entry.count()

    def reset(self, job_name: str) -> None:
        """Clear rate-limit state for *job_name*."""
        self._entries.pop(job_name, None)
