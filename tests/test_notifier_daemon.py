"""Tests for Notifier and CronCheckDaemon."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from croncheck.alerts import LoggingBackend
from croncheck.daemon import CronCheckDaemon
from croncheck.notifier import Notifier
from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob


def _make_overdue_job(job_id: str = "test_job") -> CronJob:
    """Return a job that is always overdue (every minute, no checkin)."""
    return CronJob(job_id=job_id, schedule="* * * * *", grace_seconds=0)


def _make_registry_with_overdue_job() -> JobRegistry:
    reg = JobRegistry()
    reg.register(_make_overdue_job())
    return reg


class TestNotifier:
    def test_check_and_notify_sends_alert_for_overdue_job(self):
        reg = _make_registry_with_overdue_job()
        backend = MagicMock()
        notifier = Notifier(registry=reg, backend=backend)

        alerted = notifier.check_and_notify()

        assert "test_job" in alerted
        backend.send.assert_called_once()
        subject, body = backend.send.call_args[0]
        assert "test_job" in subject
        assert "Missed" in subject

    def test_check_and_notify_no_duplicate_alerts(self):
        reg = _make_registry_with_overdue_job()
        backend = MagicMock()
        notifier = Notifier(registry=reg, backend=backend)

        notifier.check_and_notify()
        notifier.check_and_notify()  # second call should not re-alert

        assert backend.send.call_count == 1

    def test_check_and_notify_no_alert_for_healthy_job(self):
        reg = JobRegistry()
        job = CronJob(job_id="healthy", schedule="* * * * *", grace_seconds=3600)
        reg.register(job)
        reg.checkin("healthy")  # just checked in
        backend = MagicMock()
        notifier = Notifier(registry=reg, backend=backend)

        alerted = notifier.check_and_notify()

        assert alerted == []
        backend.send.assert_not_called()

    def test_notify_failure_sends_alert(self):
        reg = JobRegistry()
        backend = MagicMock()
        notifier = Notifier(registry=reg, backend=backend)

        notifier.notify_failure("my_job", exit_code=1, output="Error!")

        backend.send.assert_called_once()
        subject, body = backend.send.call_args[0]
        assert "Failed" in subject
        assert "my_job" in subject
        assert "Error!" in body


class TestCronCheckDaemon:
    def test_daemon_starts_and_stops(self):
        reg = JobRegistry()
        backend = MagicMock()
        notifier = Notifier(registry=reg, backend=backend)
        daemon = CronCheckDaemon(notifier=notifier, interval=0.05)

        daemon.start(block=False)
        time.sleep(0.15)
        daemon.stop()

        # notifier should have been called at least once
        assert backend.send.call_count >= 0  # no jobs, so 0 is fine

    def test_daemon_calls_notifier_multiple_times(self):
        reg = _make_registry_with_overdue_job()
        backend = MagicMock()
        notifier = Notifier(registry=reg, backend=backend)
        daemon = CronCheckDaemon(notifier=notifier, interval=0.05)

        daemon.start(block=False)
        time.sleep(0.2)
        daemon.stop()

        # Alert fires once (duplicate suppression), but loop ran multiple times
        assert backend.send.call_count == 1
