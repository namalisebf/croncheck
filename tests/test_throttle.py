"""Tests for croncheck.throttle.AlertThrottle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from croncheck.throttle import AlertThrottle


class TestAlertThrottle:
    def test_first_alert_always_allowed(self):
        throttle = AlertThrottle(cooldown_seconds=60)
        assert throttle.should_alert("job_a") is True

    def test_second_alert_within_cooldown_suppressed(self):
        throttle = AlertThrottle(cooldown_seconds=3600)
        throttle.should_alert("job_a")  # first — allowed
        assert throttle.should_alert("job_a") is False

    def test_alert_allowed_after_cooldown_expires(self):
        throttle = AlertThrottle(cooldown_seconds=10)
        base = 1_000_000.0
        with patch("croncheck.throttle.time.monotonic", return_value=base):
            throttle.should_alert("job_a")
        with patch("croncheck.throttle.time.monotonic", return_value=base + 11):
            assert throttle.should_alert("job_a") is True

    def test_max_alerts_silences_job(self):
        throttle = AlertThrottle(cooldown_seconds=0, max_alerts=3)
        base = 0.0
        for i in range(3):
            with patch("croncheck.throttle.time.monotonic", return_value=base + i):
                throttle.should_alert("job_a")
        # 4th call should be suppressed even with cooldown=0
        with patch("croncheck.throttle.time.monotonic", return_value=base + 10):
            assert throttle.should_alert("job_a") is False

    def test_reset_clears_entry(self):
        throttle = AlertThrottle(cooldown_seconds=3600)
        throttle.should_alert("job_a")
        throttle.reset("job_a")
        assert throttle.entry("job_a") is None
        # After reset, first alert should be allowed again
        assert throttle.should_alert("job_a") is True

    def test_reset_unknown_job_is_noop(self):
        throttle = AlertThrottle()
        throttle.reset("nonexistent")  # should not raise

    def test_reset_all_clears_all_entries(self):
        throttle = AlertThrottle(cooldown_seconds=3600)
        throttle.should_alert("job_a")
        throttle.should_alert("job_b")
        throttle.reset_all()
        assert throttle.entry("job_a") is None
        assert throttle.entry("job_b") is None

    def test_entry_increments_alert_count(self):
        throttle = AlertThrottle(cooldown_seconds=0, max_alerts=10)
        base = 0.0
        for i in range(3):
            with patch("croncheck.throttle.time.monotonic", return_value=base + i):
                throttle.should_alert("job_a")
        entry = throttle.entry("job_a")
        assert entry is not None
        assert entry.alert_count == 3

    def test_independent_jobs_tracked_separately(self):
        throttle = AlertThrottle(cooldown_seconds=3600)
        assert throttle.should_alert("job_a") is True
        assert throttle.should_alert("job_b") is True
        assert throttle.should_alert("job_a") is False
        assert throttle.should_alert("job_b") is False
