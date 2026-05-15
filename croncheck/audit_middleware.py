"""Wires AuditLog into the Notifier so every alert event is recorded."""

from __future__ import annotations

from croncheck.audit import AuditLog
from croncheck.notifier import Notifier
from croncheck.registry import JobRegistry


class AuditingNotifier:
    """Wraps Notifier and records checkin / overdue / alert events."""

    def __init__(self, notifier: Notifier, audit_log: AuditLog, registry: JobRegistry):
        self._notifier = notifier
        self._audit = audit_log
        self._registry = registry
        self._previously_overdue: set[str] = set()

    def check_and_notify(self) -> None:
        """Run the underlying notifier, then emit audit events for state changes."""
        overdue_before = set(self._previously_overdue)

        # Collect currently overdue jobs before delegating
        currently_overdue: set[str] = {
            name
            for name, job in self._registry.jobs.items()
            if job.is_overdue()
        }

        self._notifier.check_and_notify()

        # New overdue jobs
        for name in currently_overdue - overdue_before:
            self._audit.record(name, "overdue", "job became overdue")

        # Recovered jobs
        for name in overdue_before - currently_overdue:
            self._audit.record(name, "recovered", "job checked in within window")

        self._previously_overdue = currently_overdue

    def record_checkin(self, job_name: str) -> None:
        """Record a manual check-in event in the audit log."""
        self._audit.record(job_name, "checkin", "manual checkin recorded")

    def record_alert_sent(self, job_name: str, backend: str) -> None:
        self._audit.record(job_name, "alert_sent", f"via {backend}")

    def record_alert_suppressed(self, job_name: str, reason: str) -> None:
        self._audit.record(job_name, "alert_suppressed", reason)
