"""Tests for croncheck.silencer and croncheck.silencer_middleware."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from croncheck.silencer import Silencer, SilenceEntry
from croncheck.silencer_middleware import SilencedNotifier


# ---------------------------------------------------------------------------
# SilenceEntry
# ---------------------------------------------------------------------------

class TestSilenceEntry:
    def test_active_within_window(self):
        from datetime import datetime, timezone, timedelta
        entry = SilenceEntry(
            job_name="job",
            expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=5),
        )
        assert entry.is_active() is True

    def test_inactive_after_expiry(self):
        from datetime import datetime, timezone, timedelta
        entry = SilenceEntry(
            job_name="job",
            expires_at=datetime.now(tz=timezone.utc) - timedelta(seconds=1),
        )
        assert entry.is_active() is False


# ---------------------------------------------------------------------------
# Silencer
# ---------------------------------------------------------------------------

class TestSilencer:
    def test_silence_makes_job_silenced(self):
        s = Silencer()
        s.silence("backup", timedelta(hours=1), reason="maintenance")
        assert s.is_silenced("backup") is True

    def test_unknown_job_not_silenced(self):
        s = Silencer()
        assert s.is_silenced("unknown") is False

    def test_lift_removes_silence(self):
        s = Silencer()
        s.silence("backup", timedelta(hours=1))
        removed = s.lift("backup")
        assert removed is True
        assert s.is_silenced("backup") is False

    def test_lift_nonexistent_returns_false(self):
        s = Silencer()
        assert s.lift("nope") is False

    def test_expired_silence_treated_as_inactive(self):
        s = Silencer()
        s.silence("job", timedelta(seconds=-1))  # already expired
        assert s.is_silenced("job") is False

    def test_active_silences_excludes_expired(self):
        s = Silencer()
        s.silence("active_job", timedelta(hours=1))
        s.silence("expired_job", timedelta(seconds=-1))
        active = s.active_silences()
        assert "active_job" in active
        assert "expired_job" not in active

    def test_purge_expired_removes_stale_entries(self):
        s = Silencer()
        s.silence("a", timedelta(hours=1))
        s.silence("b", timedelta(seconds=-1))
        removed = s.purge_expired()
        assert removed == 1
        assert s.is_silenced("a") is True


# ---------------------------------------------------------------------------
# SilencedNotifier middleware
# ---------------------------------------------------------------------------

class TestSilencedNotifier:
    def _make_job(self, name="report"):
        job = MagicMock()
        job.name = name
        return job

    def test_check_and_notify_skips_silenced_job(self):
        inner = MagicMock()
        silencer = Silencer()
        silencer.silence("report", timedelta(hours=1))

        registry = MagicMock()
        registry.get.return_value = self._make_job("report")
        registry.active_silences = silencer.active_silences

        notifier = SilencedNotifier(inner, silencer)
        notifier.check_and_notify(registry)

        # The inner notifier must still be called (with reduced registry)
        inner.check_and_notify.assert_called_once_with(registry)
        registry.unregister.assert_called_once_with("report")

    def test_notify_failure_suppressed_when_silenced(self):
        inner = MagicMock()
        silencer = Silencer()
        silencer.silence("report", timedelta(hours=1))

        notifier = SilencedNotifier(inner, silencer)
        notifier.notify_failure(self._make_job("report"))

        inner.notify_failure.assert_not_called()

    def test_notify_failure_forwarded_when_not_silenced(self):
        inner = MagicMock()
        silencer = Silencer()

        job = self._make_job("report")
        notifier = SilencedNotifier(inner, silencer)
        notifier.notify_failure(job)

        inner.notify_failure.assert_called_once_with(job, None)
