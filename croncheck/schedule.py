"""Cron schedule parsing and next-run calculation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from croniter import croniter


@dataclass
class CronJob:
    """Represents a monitored cron job."""

    name: str
    schedule: str  # standard cron expression, e.g. "*/5 * * * *"
    grace_seconds: int = 60  # allowed delay before alerting
    last_seen: Optional[datetime] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not croniter.is_valid(self.schedule):
            raise ValueError(
                f"Invalid cron expression for job '{self.name}': {self.schedule!r}"
            )

    def expected_at(self, reference: Optional[datetime] = None) -> datetime:
        """Return the most-recently expected execution time relative to *reference*."""
        ref = reference or datetime.utcnow()
        it = croniter(self.schedule, ref)
        return it.get_prev(datetime)

    def next_run(self, reference: Optional[datetime] = None) -> datetime:
        """Return the next scheduled execution time relative to *reference*."""
        ref = reference or datetime.utcnow()
        it = croniter(self.schedule, ref)
        return it.get_next(datetime)

    def is_overdue(self, reference: Optional[datetime] = None) -> bool:
        """Return True when the job is past its grace window without a check-in."""
        ref = reference or datetime.utcnow()
        expected = self.expected_at(ref)
        deadline = expected.timestamp() + self.grace_seconds

        if self.last_seen is None:
            return ref.timestamp() > deadline

        return self.last_seen < expected and ref.timestamp() > deadline
