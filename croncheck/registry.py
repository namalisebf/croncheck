"""Job registry — tracks registered CronJob instances and their check-in state."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Iterator

from croncheck.schedule import CronJob

logger = logging.getLogger(__name__)


class JobRegistry:
    """Thread-safe registry of CronJob instances."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}
        self._lock = threading.Lock()
        self._listeners: list[Callable[[str, CronJob], None]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, job: CronJob) -> None:
        """Add a job to the registry, replacing any existing entry with the same name."""
        with self._lock:
            self._jobs[job.name] = job
        logger.debug("Registered job '%s'", job.name)

    def unregister(self, name: str) -> None:
        """Remove a job by name; silently ignores unknown names."""
        with self._lock:
            removed = self._jobs.pop(name, None)
        if removed:
            logger.debug("Unregistered job '%s'", name)

    # ------------------------------------------------------------------
    # Check-in
    # ------------------------------------------------------------------

    def checkin(self, name: str, *, success: bool = True) -> None:
        """Record a check-in for *name*, updating last_checkin timestamp."""
        with self._lock:
            job = self._jobs.get(name)
        if job is None:
            logger.warning("Check-in for unknown job '%s' ignored", name)
            return
        job.last_checkin = datetime.now(tz=timezone.utc)
        job.last_success = success
        logger.debug("Check-in recorded for '%s' (success=%s)", name, success)
        for listener in self._listeners:
            try:
                listener(name, job)
            except Exception:  # noqa: BLE001
                logger.exception("Listener raised an exception during check-in for '%s'", name)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, name: str) -> CronJob | None:
        """Return the job with *name*, or *None* if not found."""
        with self._lock:
            return self._jobs.get(name)

    def all_jobs(self) -> list[CronJob]:
        """Return a snapshot list of all registered jobs."""
        with self._lock:
            return list(self._jobs.values())

    def overdue_jobs(self) -> list[CronJob]:
        """Return all jobs currently considered overdue."""
        return [job for job in self.all_jobs() if job.is_overdue()]

    def __iter__(self) -> Iterator[CronJob]:
        return iter(self.all_jobs())

    def __len__(self) -> int:
        with self._lock:
            return len(self._jobs)

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def add_checkin_listener(self, fn: Callable[[str, CronJob], None]) -> None:
        """Register a callback invoked after every successful check-in."""
        self._listeners.append(fn)
