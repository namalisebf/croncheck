"""Notifier middleware that enforces per-job alert rate limits."""
from __future__ import annotations

import logging
from typing import Optional

from croncheck.notifier import Notifier
from croncheck.ratelimit import RateLimiter
from croncheck.registry import JobRegistry

logger = logging.getLogger(__name__)


class RateLimitedNotifier:
    """Wraps a :class:`Notifier` and suppresses alerts that exceed the
    configured sliding-window rate limit.

    Parameters
    ----------
    notifier:
        The underlying notifier to delegate allowed alerts to.
    rate_limiter:
        A :class:`RateLimiter` instance that decides whether an alert
        should be dispatched.
    """

    def __init__(self, notifier: Notifier, rate_limiter: Optional[RateLimiter] = None) -> None:
        self._notifier = notifier
        self._limiter = rate_limiter or RateLimiter()

    # ------------------------------------------------------------------
    # Public API mirrors Notifier
    # ------------------------------------------------------------------

    def check_and_notify(self, registry: JobRegistry) -> None:
        """Check all jobs and send rate-limited alerts for overdue ones."""
        for name, job in list(registry.jobs.items()):
            if not job.is_overdue(registry.last_checkin(name)):
                continue
            if not self._limiter.is_allowed(name):
                logger.debug(
                    "Rate limit reached for job '%s'; suppressing alert.", name
                )
                continue
            self._notifier.notify_failure(job)
            self._limiter.record(name)
            logger.debug(
                "Alert dispatched for job '%s' (%d in window).",
                name,
                self._limiter.current_count(name),
            )

    def notify_failure(self, job) -> None:  # type: ignore[override]
        """Send a single failure alert, subject to rate limiting."""
        if not self._limiter.is_allowed(job.name):
            logger.debug(
                "Rate limit reached for job '%s'; suppressing alert.", job.name
            )
            return
        self._notifier.notify_failure(job)
        self._limiter.record(job.name)

    def reset(self, job_name: str) -> None:
        """Reset the rate-limit counter for *job_name*."""
        self._limiter.reset(job_name)
