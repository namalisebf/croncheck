"""Notifier middleware that attaches a correlation ID to every alert cycle."""

from __future__ import annotations

from typing import Optional

from croncheck.correlation import CorrelationContext, current_correlation_id
from croncheck.notifier import Notifier
from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob


class CorrelatingNotifier:
    """Wraps a :class:`~croncheck.notifier.Notifier` and ensures every
    ``check_and_notify`` sweep runs inside a fresh :class:`CorrelationContext`.

    The same correlation ID is therefore visible to all alert backends,
    middleware layers, and audit records that execute within that sweep.
    """

    def __init__(self, inner: Notifier, registry: JobRegistry) -> None:
        self._inner = inner
        self._registry = registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_notify(self) -> Optional[str]:
        """Run one check sweep under a fresh correlation ID.

        Returns the correlation ID used for the sweep so callers (e.g. tests
        or audit layers) can reference it.
        """
        with CorrelationContext() as ctx:
            self._inner.check_and_notify()
            return ctx.correlation_id

    def notify_failure(self, job: CronJob, reason: str) -> Optional[str]:
        """Send a single failure alert, reusing any active correlation ID or
        creating a new one if none is set.
        """
        existing = current_correlation_id()
        if existing:
            self._inner.notify_failure(job, reason)
            return existing

        with CorrelationContext() as ctx:
            self._inner.notify_failure(job, reason)
            return ctx.correlation_id

    def record_checkin(self, job_name: str) -> None:
        """Delegate check-in recording to the inner notifier (if supported)."""
        if hasattr(self._inner, "record_checkin"):
            self._inner.record_checkin(job_name)  # type: ignore[union-attr]
