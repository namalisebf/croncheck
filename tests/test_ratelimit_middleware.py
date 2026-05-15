"""Tests for croncheck.ratelimit_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from croncheck.ratelimit import RateLimiter
from croncheck.ratelimit_middleware import RateLimitedNotifier


def _make_job(name: str, overdue: bool = True):
    job = MagicMock()
    job.name = name
    job.is_overdue.return_value = overdue
    return job


def _make_registry(*jobs):
    registry = MagicMock()
    registry.jobs = {j.name: j for j in jobs}
    registry.last_checkin.return_value = None
    return registry


class TestRateLimitedNotifier:
    def test_alert_dispatched_when_allowed(self):
        inner = MagicMock()
        rl = RateLimiter(window_seconds=60, max_alerts=3)
        notifier = RateLimitedNotifier(inner, rl)
        job = _make_job("backup")
        notifier.notify_failure(job)
        inner.notify_failure.assert_called_once_with(job)

    def test_alert_suppressed_when_limit_reached(self):
        inner = MagicMock()
        rl = RateLimiter(window_seconds=60, max_alerts=1)
        notifier = RateLimitedNotifier(inner, rl)
        job = _make_job("backup")
        notifier.notify_failure(job)  # allowed
        notifier.notify_failure(job)  # suppressed
        inner.notify_failure.assert_called_once_with(job)

    def test_check_and_notify_dispatches_overdue(self):
        inner = MagicMock()
        rl = RateLimiter(window_seconds=60, max_alerts=5)
        notifier = RateLimitedNotifier(inner, rl)
        job = _make_job("sync", overdue=True)
        registry = _make_registry(job)
        notifier.check_and_notify(registry)
        inner.notify_failure.assert_called_once_with(job)

    def test_check_and_notify_skips_non_overdue(self):
        inner = MagicMock()
        rl = RateLimiter(window_seconds=60, max_alerts=5)
        notifier = RateLimitedNotifier(inner, rl)
        job = _make_job("sync", overdue=False)
        registry = _make_registry(job)
        notifier.check_and_notify(registry)
        inner.notify_failure.assert_not_called()

    def test_check_and_notify_suppresses_after_limit(self):
        inner = MagicMock()
        rl = RateLimiter(window_seconds=60, max_alerts=2)
        notifier = RateLimitedNotifier(inner, rl)
        job = _make_job("etl", overdue=True)
        registry = _make_registry(job)
        for _ in range(5):
            notifier.check_and_notify(registry)
        assert inner.notify_failure.call_count == 2

    def test_reset_allows_alerts_again(self):
        inner = MagicMock()
        rl = RateLimiter(window_seconds=60, max_alerts=1)
        notifier = RateLimitedNotifier(inner, rl)
        job = _make_job("report")
        notifier.notify_failure(job)
        notifier.notify_failure(job)  # suppressed
        notifier.reset("report")
        notifier.notify_failure(job)  # allowed again
        assert inner.notify_failure.call_count == 2

    def test_default_rate_limiter_created_when_none_provided(self):
        inner = MagicMock()
        notifier = RateLimitedNotifier(inner)
        assert notifier._limiter is not None
        assert isinstance(notifier._limiter, RateLimiter)
