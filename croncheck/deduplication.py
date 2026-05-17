"""Alert deduplication: suppress identical alerts within a configurable window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class DedupeEntry:
    job_name: str
    alert_type: str
    first_seen: float = field(default_factory=time.monotonic)
    last_seen: float = field(default_factory=time.monotonic)
    count: int = 1

    def touch(self) -> None:
        self.last_seen = time.monotonic()
        self.count += 1

    def age_seconds(self) -> float:
        return time.monotonic() - self.first_seen


class AlertDeduplicator:
    """Tracks recent alerts and suppresses duplicates within *window_seconds*.

    An alert is considered a duplicate when the same (job_name, alert_type)
    pair has already been dispatched within the deduplication window.
    """

    def __init__(self, window_seconds: float = 300.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = window_seconds
        self._entries: Dict[Tuple[str, str], DedupeEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_duplicate(self, job_name: str, alert_type: str = "overdue") -> bool:
        """Return True if an identical alert was already sent within the window."""
        self._evict_expired()
        key = (job_name, alert_type)
        return key in self._entries

    def record(self, job_name: str, alert_type: str = "overdue") -> None:
        """Record that an alert was dispatched."""
        key = (job_name, alert_type)
        if key in self._entries:
            self._entries[key].touch()
        else:
            self._entries[key] = DedupeEntry(job_name=job_name, alert_type=alert_type)

    def reset(self, job_name: str, alert_type: Optional[str] = None) -> None:
        """Remove deduplication state for *job_name* (optionally for a specific type)."""
        if alert_type is not None:
            self._entries.pop((job_name, alert_type), None)
        else:
            keys = [k for k in self._entries if k[0] == job_name]
            for k in keys:
                del self._entries[k]

    def entry(self, job_name: str, alert_type: str = "overdue") -> Optional[DedupeEntry]:
        return self._entries.get((job_name, alert_type))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [
            k for k, e in self._entries.items()
            if (now - e.first_seen) >= self._window
        ]
        for k in expired:
            del self._entries[k]
