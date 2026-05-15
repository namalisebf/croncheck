"""Alert throttling to prevent notification storms."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleEntry:
    first_alert_at: float
    last_alert_at: float
    alert_count: int = 1


class AlertThrottle:
    """Suppress repeated alerts for the same job within a cooldown window."""

    def __init__(self, cooldown_seconds: int = 3600, max_alerts: int = 5) -> None:
        """Args:
            cooldown_seconds: Minimum seconds between repeated alerts per job.
            max_alerts: Maximum alerts per job before silencing until reset.
        """
        self.cooldown_seconds = cooldown_seconds
        self.max_alerts = max_alerts
        self._entries: Dict[str, ThrottleEntry] = {}

    def should_alert(self, job_name: str) -> bool:
        """Return True if an alert should be sent for *job_name* right now."""
        now = time.monotonic()
        entry = self._entries.get(job_name)

        if entry is None:
            self._entries[job_name] = ThrottleEntry(
                first_alert_at=now, last_alert_at=now
            )
            return True

        if entry.alert_count >= self.max_alerts:
            return False

        if (now - entry.last_alert_at) < self.cooldown_seconds:
            return False

        entry.last_alert_at = now
        entry.alert_count += 1
        return True

    def reset(self, job_name: str) -> None:
        """Clear throttle state for *job_name* (e.g. after a successful check-in)."""
        self._entries.pop(job_name, None)

    def reset_all(self) -> None:
        """Clear all throttle state."""
        self._entries.clear()

    def entry(self, job_name: str) -> Optional[ThrottleEntry]:
        """Return the current ThrottleEntry for *job_name*, or None."""
        return self._entries.get(job_name)
