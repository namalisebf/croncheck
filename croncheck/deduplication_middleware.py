"""Notifier middleware that wraps an inner Notifier with alert deduplication."""

from __future__ import annotations

from typing import Optional

from croncheck.deduplication import AlertDeduplicator
from croncheck.notifier import Notifier
from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob


class DeduplicatingNotifier:
    """Wraps a :class:`~croncheck.notifier.Notifier` and suppresses duplicate
    alerts for the same job within a configurable time window.

    A duplicate is defined as the same (job_name, alert_type) pair being
    triggered again before *window_seconds* have elapsed since the first alert.
    Once a job checks in successfully the deduplication state for that job is
    cleared so the next overdue period triggers a fresh alert.
    """

    def __init__(
        self,
        inner: Notifier,
        registry: JobRegistry,
        window_seconds: float = 300.0,
    ) -> None:
        self._inner = inner
        self._registry = registry
        self._dedup = AlertDeduplicator(window_seconds=window_seconds)

    # ------------------------------------------------------------------
    # Notifier-compatible interface
    # ------------------------------------------------------------------

    def check_and_notify(self) -> None:
        """Check all jobs and forward alerts only for non-duplicate overdue jobs."""
        for job in self._registry.all_jobs():
            last_checkin = self._registry.last_checkin(job.name)
            if job.is_overdue(last_checkin):
                self._maybe_alert(job, "overdue")

    def notify_failure(self, job_name: str, detail: Optional[str] = None) -> None:
        """Forward a failure notification unless it is a duplicate."""
        if not self._dedup.is_duplicate(job_name, "failure"):
            self._dedup.record(job_name, "failure")
            self._inner.notify_failure(job_name, detail)

    def record_checkin(self, job_name: str) -> None:
        """Propagate a check-in and clear deduplication state for that job."""
        self._registry.checkin(job_name)
        self._dedup.reset(job_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _maybe_alert(self, job: CronJob, alert_type: str) -> None:
        if self._dedup.is_duplicate(job.name, alert_type):
            return
        self._dedup.record(job.name, alert_type)
        # Delegate actual alert dispatch to the inner notifier
        self._inner.notify_failure(
            job.name,
            detail=f"Job '{job.name}' is overdue (type={alert_type})",
        )
