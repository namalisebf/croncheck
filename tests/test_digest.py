"""Tests for croncheck.digest and croncheck.digest_sender."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from croncheck.digest import DigestEntry, DigestReport, build_digest
from croncheck.digest_sender import DigestSender


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc
_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_job(name: str, overdue: bool, last_checkin=None):
    job = MagicMock()
    job.name = name
    job.next_run.return_value = _NOW + timedelta(minutes=5)
    return job


def _make_registry(jobs):
    """jobs: list of (name, overdue, last_checkin)"""
    registry = MagicMock()
    job_objs = [_make_job(name, overdue, lc) for name, overdue, lc in jobs]
    registry.list_jobs.return_value = job_objs
    registry.is_overdue.side_effect = lambda n: next(
        overdue for name, overdue, _ in jobs if name == n
    )
    registry.last_checkin.side_effect = lambda n: next(
        lc for name, _, lc in jobs if name == n
    )
    return registry


# ---------------------------------------------------------------------------
# DigestReport
# ---------------------------------------------------------------------------

class TestDigestReport:
    def test_overdue_and_healthy_counts(self):
        report = DigestReport()
        report.entries = [
            DigestEntry("a", True, None, _NOW),
            DigestEntry("b", False, _NOW, _NOW),
            DigestEntry("c", True, None, _NOW),
        ]
        assert report.overdue_count == 2
        assert report.healthy_count == 1

    def test_format_text_contains_job_names(self):
        report = DigestReport(generated_at=_NOW)
        report.entries = [
            DigestEntry("backup", False, _NOW, _NOW + timedelta(hours=1)),
        ]
        text = report.format_text()
        assert "backup" in text
        assert "OK" in text

    def test_format_text_marks_overdue(self):
        report = DigestReport(generated_at=_NOW)
        report.entries = [
            DigestEntry("sync", True, None, _NOW + timedelta(minutes=10)),
        ]
        text = report.format_text()
        assert "OVERDUE" in text
        assert "never" in text


# ---------------------------------------------------------------------------
# build_digest
# ---------------------------------------------------------------------------

class TestBuildDigest:
    def test_entries_match_registry_jobs(self):
        registry = _make_registry([("job1", False, _NOW), ("job2", True, None)])
        report = build_digest(registry)
        names = {e.job_name for e in report.entries}
        assert names == {"job1", "job2"}

    def test_overdue_jobs_sorted_first(self):
        registry = _make_registry([("alpha", False, _NOW), ("beta", True, None)])
        report = build_digest(registry)
        assert report.entries[0].job_name == "beta"


# ---------------------------------------------------------------------------
# DigestSender
# ---------------------------------------------------------------------------

class TestDigestSender:
    def _make_sender(self, interval_seconds=0.05):
        registry = _make_registry([("j", False, _NOW)])
        backend = MagicMock()
        sender = DigestSender(
            registry, backend, interval=timedelta(seconds=interval_seconds)
        )
        return sender, backend

    def test_send_now_calls_backend(self):
        sender, backend = self._make_sender()
        sender.send_now()
        backend.send.assert_called_once()
        subject, body = backend.send.call_args[0]
        assert "croncheck digest" in subject

    def test_send_now_returns_report(self):
        sender, _ = self._make_sender()
        report = sender.send_now()
        assert isinstance(report, DigestReport)

    def test_start_stop_does_not_raise(self):
        sender, _ = self._make_sender(interval_seconds=10)
        sender.start()
        sender.stop()

    def test_periodic_fire_calls_backend(self):
        fired = threading.Event()
        sender, backend = self._make_sender(interval_seconds=0.05)
        orig_send = sender.send_now

        def _patched():
            result = orig_send()
            fired.set()
            return result

        sender.send_now = _patched
        sender.start()
        fired.wait(timeout=2)
        sender.stop()
        assert backend.send.called
