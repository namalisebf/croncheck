"""Notifier middleware that skips alerts for silenced jobs."""

from __future__ import annotations

import logging
from typing import Optional

from croncheck.notifier import Notifier
from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob
from croncheck.silencer import Silencer

logger = logging.getLogger(__name__)


class SilencedNotifier:
    """Wraps a :class:`Notifier` and suppresses alerts for silenced jobs.

    All other behaviour (overdue detection, failure notifications) is
    delegated to the inner notifier unchanged.
    """

    def __init__(self, inner: Notifier, silencer: Silencer) -> None:
        self._inner = inner
        self._silencer = silencer

    # ------------------------------------------------------------------
    # Public API mirrors Notifier
    # ------------------------------------------------------------------

    def check_and_notify(self, registry: JobRegistry) -> None:
        """Check all jobs, skipping any that are currently silenced."""
        silenced = self._silencer.active_silences()
        if silenced:
            logger.debug(
                "Silencer: %d job(s) muted: %s",
                len(silenced),
                list(silenced),
            )

        # Temporarily unregister silenced jobs, delegate, then restore.
        removed: dict[str, CronJob] = {}
        for name in list(silenced):
            job = registry.get(name)
            if job is not None:
                registry.unregister(name)
                removed[name] = job

        try:
            self._inner.check_and_notify(registry)
        finally:
            for name, job in removed.items():
                registry.register(job)

    def notify_failure(
        self,
        job: CronJob,
        message: Optional[str] = None,
    ) -> None:
        """Forward failure alerts unless the job is silenced."""
        if self._silencer.is_silenced(job.name):
            logger.debug("Silencer: suppressing failure alert for %r", job.name)
            return
        self._inner.notify_failure(job, message)
