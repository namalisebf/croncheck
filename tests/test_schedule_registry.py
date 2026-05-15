"""Tests for CronJob scheduling logic and JobRegistry."""

from datetime import datetime, timedelta

import pytest

from croncheck.schedule import CronJob
from croncheck.registry import JobRegistry


# ---------------------------------------------------------------------------
# CronJob tests
# ---------------------------------------------------------------------------

class TestCronJob:
    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronJob(name="bad", schedule="not-a-cron")

    def test_expected_at_returns_past_datetime(self):
        job = CronJob(name="minutely", schedule="* * * * *")
        ref = datetime(2024, 6, 1, 12, 30, 45)
        expected = job.expected_at(ref)
        assert expected <= ref

    def test_next_run_returns_future_datetime(self):
        job = CronJob(name="minutely", schedule="* * * * *")
        ref = datetime(2024, 6, 1, 12, 30, 45)
        nxt = job.next_run(ref)
        assert nxt > ref

    def test_is_overdue_no_checkin_past_grace(self):
        job = CronJob(name="minutely", schedule="* * * * *", grace_seconds=30)
        # Reference is 90 s after the top of the minute → well past grace
        ref = datetime(2024, 6, 1, 12, 31, 90)
        assert job.is_overdue(ref)

    def test_is_not_overdue_within_grace(self):
        job = CronJob(name="minutely", schedule="* * * * *", grace_seconds=120)
        ref = datetime(2024, 6, 1, 12, 31, 10)  # 10 s after expected
        assert not job.is_overdue(ref)

    def test_is_not_overdue_after_checkin(self):
        job = CronJob(name="minutely", schedule="* * * * *", grace_seconds=30)
        ref = datetime(2024, 6, 1, 12, 31, 90)
        job.last_seen = datetime(2024, 6, 1, 12, 31, 5)  # checked in this minute
        assert not job.is_overdue(ref)


# ---------------------------------------------------------------------------
# JobRegistry tests
# ---------------------------------------------------------------------------

class TestJobRegistry:
    def _make_registry(self) -> JobRegistry:
        reg = JobRegistry()
        reg.register(CronJob(name="heartbeat", schedule="* * * * *", grace_seconds=30))
        return reg

    def test_register_and_contains(self):
        reg = self._make_registry()
        assert "heartbeat" in reg
        assert len(reg) == 1

    def test_unregister_removes_job(self):
        reg = self._make_registry()
        reg.unregister("heartbeat")
        assert "heartbeat" not in reg

    def test_checkin_updates_last_seen(self):
        reg = self._make_registry()
        ts = datetime(2024, 6, 1, 12, 31, 5)
        reg.checkin("heartbeat", at=ts)
        assert reg.get("heartbeat").last_seen == ts

    def test_checkin_unknown_job_raises(self):
        reg = self._make_registry()
        with pytest.raises(KeyError):
            reg.checkin("ghost")

    def test_overdue_jobs_detected(self):
        reg = self._make_registry()
        ref = datetime(2024, 6, 1, 12, 31, 90)
        overdue = reg.overdue_jobs(reference=ref)
        assert any(j.name == "heartbeat" for j in overdue)

    def test_no_overdue_after_checkin(self):
        reg = self._make_registry()
        ref = datetime(2024, 6, 1, 12, 31, 90)
        reg.checkin("heartbeat", at=datetime(2024, 6, 1, 12, 31, 5))
        assert reg.overdue_jobs(reference=ref) == []
