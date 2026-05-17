"""Tests for croncheck.deduplication and croncheck.deduplication_middleware."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from croncheck.deduplication import AlertDeduplicator, DedupeEntry
from croncheck.deduplication_middleware import DeduplicatingNotifier


# ---------------------------------------------------------------------------
# AlertDeduplicator
# ---------------------------------------------------------------------------

class TestAlertDeduplicator:
    def test_first_alert_not_duplicate(self):
        d = AlertDeduplicator(window_seconds=60)
        assert d.is_duplicate("backup") is False

    def test_after_record_is_duplicate(self):
        d = AlertDeduplicator(window_seconds=60)
        d.record("backup")
        assert d.is_duplicate("backup") is True

    def test_different_job_not_duplicate(self):
        d = AlertDeduplicator(window_seconds=60)
        d.record("backup")
        assert d.is_duplicate("cleanup") is False

    def test_different_alert_type_not_duplicate(self):
        d = AlertDeduplicator(window_seconds=60)
        d.record("backup", "overdue")
        assert d.is_duplicate("backup", "failure") is False

    def test_entry_count_increments_on_duplicate_record(self):
        d = AlertDeduplicator(window_seconds=60)
        d.record("backup")
        d.record("backup")
        assert d.entry("backup").count == 2

    def test_reset_clears_specific_type(self):
        d = AlertDeduplicator(window_seconds=60)
        d.record("backup", "overdue")
        d.record("backup", "failure")
        d.reset("backup", "overdue")
        assert d.is_duplicate("backup", "overdue") is False
        assert d.is_duplicate("backup", "failure") is True

    def test_reset_all_types_for_job(self):
        d = AlertDeduplicator(window_seconds=60)
        d.record("backup", "overdue")
        d.record("backup", "failure")
        d.reset("backup")
        assert d.is_duplicate("backup", "overdue") is False
        assert d.is_duplicate("backup", "failure") is False

    def test_expired_entries_evicted(self):
        d = AlertDeduplicator(window_seconds=1)
        d.record("backup")
        # Simulate passage of time beyond the window
        with patch("croncheck.deduplication.time.monotonic", return_value=time.monotonic() + 2):
            assert d.is_duplicate("backup") is False

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            AlertDeduplicator(window_seconds=0)


# ---------------------------------------------------------------------------
# DeduplicatingNotifier
# ---------------------------------------------------------------------------

def _make_overdue_job(name="backup"):
    job = MagicMock()
    job.name = name
    job.is_overdue.return_value = True
    return job


def _make_registry(*jobs):
    registry = MagicMock()
    registry.all_jobs.return_value = list(jobs)
    registry.last_checkin.return_value = None
    return registry


class TestDeduplicatingNotifier:
    def test_alert_dispatched_on_first_overdue(self):
        job = _make_overdue_job()
        registry = _make_registry(job)
        inner = MagicMock()
        notifier = DeduplicatingNotifier(inner, registry, window_seconds=60)
        notifier.check_and_notify()
        inner.notify_failure.assert_called_once()

    def test_duplicate_alert_suppressed(self):
        job = _make_overdue_job()
        registry = _make_registry(job)
        inner = MagicMock()
        notifier = DeduplicatingNotifier(inner, registry, window_seconds=60)
        notifier.check_and_notify()
        notifier.check_and_notify()
        assert inner.notify_failure.call_count == 1

    def test_checkin_resets_dedup_state(self):
        job = _make_overdue_job()
        registry = _make_registry(job)
        inner = MagicMock()
        notifier = DeduplicatingNotifier(inner, registry, window_seconds=60)
        notifier.check_and_notify()
        notifier.record_checkin(job.name)
        notifier.check_and_notify()
        assert inner.notify_failure.call_count == 2

    def test_notify_failure_deduplication(self):
        registry = _make_registry()
        inner = MagicMock()
        notifier = DeduplicatingNotifier(inner, registry, window_seconds=60)
        notifier.notify_failure("backup", detail="exit 1")
        notifier.notify_failure("backup", detail="exit 1")
        assert inner.notify_failure.call_count == 1
