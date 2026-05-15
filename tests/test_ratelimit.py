"""Tests for croncheck.ratelimit."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from croncheck.ratelimit import RateLimiter, WindowEntry


class TestWindowEntry:
    def test_record_increments_count(self):
        entry = WindowEntry()
        entry.record()
        entry.record()
        assert entry.count() == 2

    def test_prune_removes_old_timestamps(self):
        entry = WindowEntry()
        with patch("croncheck.ratelimit.time.monotonic", return_value=0.0):
            entry.record()
        with patch("croncheck.ratelimit.time.monotonic", return_value=10.0):
            entry.prune(window_seconds=5.0)
            assert entry.count() == 0

    def test_prune_keeps_recent_timestamps(self):
        entry = WindowEntry()
        with patch("croncheck.ratelimit.time.monotonic", return_value=0.0):
            entry.record()
        with patch("croncheck.ratelimit.time.monotonic", return_value=3.0):
            entry.prune(window_seconds=5.0)
            assert entry.count() == 1


class TestRateLimiter:
    def test_first_alert_always_allowed(self):
        rl = RateLimiter(window_seconds=60.0, max_alerts=3)
        assert rl.is_allowed("job-a") is True

    def test_alert_blocked_after_max(self):
        rl = RateLimiter(window_seconds=60.0, max_alerts=2)
        rl.record("job-a")
        rl.record("job-a")
        assert rl.is_allowed("job-a") is False

    def test_alert_allowed_after_window_expires(self):
        rl = RateLimiter(window_seconds=10.0, max_alerts=1)
        with patch("croncheck.ratelimit.time.monotonic", return_value=0.0):
            rl.record("job-a")
            assert rl.is_allowed("job-a") is False
        with patch("croncheck.ratelimit.time.monotonic", return_value=11.0):
            assert rl.is_allowed("job-a") is True

    def test_current_count_reflects_window(self):
        rl = RateLimiter(window_seconds=10.0, max_alerts=5)
        with patch("croncheck.ratelimit.time.monotonic", return_value=0.0):
            rl.record("job-b")
            rl.record("job-b")
        with patch("croncheck.ratelimit.time.monotonic", return_value=5.0):
            assert rl.current_count("job-b") == 2
        with patch("croncheck.ratelimit.time.monotonic", return_value=11.0):
            assert rl.current_count("job-b") == 0

    def test_reset_clears_state(self):
        rl = RateLimiter(window_seconds=60.0, max_alerts=1)
        rl.record("job-c")
        assert rl.is_allowed("job-c") is False
        rl.reset("job-c")
        assert rl.is_allowed("job-c") is True

    def test_independent_jobs_do_not_interfere(self):
        rl = RateLimiter(window_seconds=60.0, max_alerts=1)
        rl.record("job-x")
        assert rl.is_allowed("job-y") is True

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimiter(window_seconds=0)

    def test_invalid_max_alerts_raises(self):
        with pytest.raises(ValueError, match="max_alerts"):
            RateLimiter(max_alerts=0)
