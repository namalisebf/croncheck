"""Notifier: checks registry for overdue/failed jobs and dispatches alerts."""

from __future__ import annotations

import logging
from typing import Optional, Set

from croncheck.alerts import AlertBackend
from croncheck.registry import JobRegistry
from croncheck.throttle import AlertThrottle

logger = logging.getLogger(__name__)


class Notifier:
    """Polls a JobRegistry and sends alerts via an AlertBackend."""

    def __init__(
        self,
        registry: JobRegistry,
        backend: AlertBackend,
        throttle: Optional[AlertThrottle] = None,
    ) -> None:
        self.registry = registry
        self.backend = backend
        self.throttle: AlertThrottle = throttle or AlertThrottle()
        self._alerted: Set[str] = set()

    def check_and_notify(self) -> None:
        """Inspect all registered jobs; alert for any that are overdue."""
        for name, job in self.registry.jobs.items():
            if self.registry.is_overdue(name):
                if self.throttle.should_alert(name):
                    self.backend.send(
                        subject=f"[croncheck] Job overdue: {name}",
                        body=(
                            f"Job '{name}' has not checked in within its "
                            f"schedule + grace period ({job.grace_seconds}s)."
                        ),
                    )
                    self._alerted.add(name)
                    logger.warning("Alert sent for overdue job '%s'.", name)
                else:
                    logger.debug("Alert for '%s' suppressed by throttle.", name)
            else:
                if name in self._alerted:
                    logger.info("Job '%s' recovered; resetting throttle.", name)
                    self.throttle.reset(name)
                    self._alerted.discard(name)

    def notify_failure(self, job_name: str, reason: str) -> None:
        """Immediately send a failure alert, subject to throttle."""
        if self.throttle.should_alert(job_name):
            self.backend.send(
                subject=f"[croncheck] Job failed: {job_name}",
                body=f"Job '{job_name}' reported a failure: {reason}",
            )
            self._alerted.add(job_name)
            logger.warning("Failure alert sent for job '%s': %s", job_name, reason)
        else:
            logger.debug(
                "Failure alert for '%s' suppressed by throttle.", job_name
            )
