"""Notifier ties the registry to alert backends."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from croncheck.alerts import AlertBackend
    from croncheck.registry import JobRegistry

logger = logging.getLogger(__name__)

_MISSED_SUBJECT = "[croncheck] Missed run: {job_id}"
_MISSED_BODY = (
    "Job '{job_id}' was expected at {expected_at} (grace {grace}s) "
    "but has not checked in.\nSchedule: {schedule}"
)

_FAILED_SUBJECT = "[croncheck] Failed run: {job_id}"
_FAILED_BODY = (
    "Job '{job_id}' reported a failure at {checkin_time}.\n"
    "Exit code: {exit_code}\nOutput:\n{output}"
)


@dataclass
class Notifier:
    """Checks the registry for overdue jobs and dispatches alerts."""

    registry: JobRegistry
    backend: AlertBackend
    _alerted: set[str] = field(default_factory=set, init=False)

    def check_and_notify(self) -> list[str]:
        """Scan all jobs; send alerts for newly overdue ones. Returns alerted job IDs."""
        now = datetime.now(tz=timezone.utc)
        newly_alerted: list[str] = []

        for job in self.registry.all_jobs():
            if not job.is_overdue(now):
                # Clear alert state so we re-alert next time it goes overdue
                self._alerted.discard(job.job_id)
                continue

            if job.job_id in self._alerted:
                continue

            expected = job.expected_at(now)
            subject = _MISSED_SUBJECT.format(job_id=job.job_id)
            body = _MISSED_BODY.format(
                job_id=job.job_id,
                expected_at=expected.isoformat() if expected else "unknown",
                grace=job.grace_seconds,
                schedule=job.schedule,
            )
            self.backend.send(subject, body)
            self._alerted.add(job.job_id)
            newly_alerted.append(job.job_id)
            logger.warning("Alert sent for overdue job '%s'", job.job_id)

        return newly_alerted

    def notify_failure(
        self,
        job_id: str,
        exit_code: int,
        output: str = "",
    ) -> None:
        """Send an immediate failure alert for a job that reported an error."""
        subject = _FAILED_SUBJECT.format(job_id=job_id)
        body = _FAILED_BODY.format(
            job_id=job_id,
            checkin_time=datetime.now(tz=timezone.utc).isoformat(),
            exit_code=exit_code,
            output=output or "(no output)",
        )
        self.backend.send(subject, body)
        logger.warning("Failure alert sent for job '%s' (exit %d)", job_id, exit_code)
