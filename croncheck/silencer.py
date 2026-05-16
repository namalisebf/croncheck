"""Silence (mute) specific cron jobs for a configurable duration."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class SilenceEntry:
    job_name: str
    expires_at: datetime
    reason: str = ""

    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Return True if the silence window is still in effect."""
        now = now or _now()
        return now < self.expires_at


class Silencer:
    """Thread-safe registry of temporarily silenced jobs."""

    def __init__(self) -> None:
        self._entries: Dict[str, SilenceEntry] = {}
        self._lock = threading.Lock()

    def silence(
        self,
        job_name: str,
        duration: timedelta,
        reason: str = "",
    ) -> SilenceEntry:
        """Silence *job_name* for *duration*. Overwrites any existing entry."""
        entry = SilenceEntry(
            job_name=job_name,
            expires_at=_now() + duration,
            reason=reason,
        )
        with self._lock:
            self._entries[job_name] = entry
        return entry

    def lift(self, job_name: str) -> bool:
        """Remove a silence entry early. Returns True if one existed."""
        with self._lock:
            return self._entries.pop(job_name, None) is not None

    def is_silenced(self, job_name: str) -> bool:
        """Return True if *job_name* currently has an active silence."""
        with self._lock:
            entry = self._entries.get(job_name)
        if entry is None:
            return False
        if entry.is_active():
            return True
        # Lazily remove expired entries
        with self._lock:
            self._entries.pop(job_name, None)
        return False

    def active_silences(self) -> Dict[str, SilenceEntry]:
        """Return a snapshot of currently active silence entries."""
        now = _now()
        with self._lock:
            return {
                name: entry
                for name, entry in self._entries.items()
                if entry.is_active(now)
            }

    def purge_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = _now()
        with self._lock:
            expired = [n for n, e in self._entries.items() if not e.is_active(now)]
            for name in expired:
                del self._entries[name]
        return len(expired)
