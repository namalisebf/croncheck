"""In-memory registry that tracks all monitored cron jobs."""

from datetime import datetime
from typing import Dict, Iterator, List

from .schedule import CronJob


class JobRegistry:
    """Central store for :class:`CronJob` instances."""

    def __init__(self) -> None:
        self._jobs: Dict[str, CronJob] = {}

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def register(self, job: CronJob) -> None:
        """Add or replace a job in the registry."""
        self._jobs[job.name] = job

    def unregister(self, name: str) -> None:
        """Remove a job by name; silently ignores unknown names."""
        self._jobs.pop(name, None)

    def checkin(self, name: str, at: datetime | None = None) -> None:
        """Record a successful execution for *name*.

        Raises
        ------
        KeyError
            If *name* is not registered.
        """
        job = self._jobs[name]  # intentional KeyError on unknown job
        job.last_seen = at or datetime.utcnow()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get(self, name: str) -> CronJob:
        return self._jobs[name]

    def all_jobs(self) -> Iterator[CronJob]:
        """Iterate over every registered job."""
        yield from self._jobs.values()

    def overdue_jobs(self, reference: datetime | None = None) -> List[CronJob]:
        """Return jobs that are currently overdue."""
        ref = reference or datetime.utcnow()
        return [j for j in self._jobs.values() if j.is_overdue(ref)]

    def __len__(self) -> int:
        return len(self._jobs)

    def __contains__(self, name: str) -> bool:
        return name in self._jobs
