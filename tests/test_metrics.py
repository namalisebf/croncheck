"""Tests for croncheck.metrics."""
from __future__ import annotations

import time

import pytest

from croncheck.metrics import JobMetrics, MetricsCollector


class TestJobMetrics:
    def test_initial_values(self):
        m = JobMetrics(job_name="backup")
        assert m.total_checkins == 0
        assert m.missed_runs == 0
        assert m.last_checkin_ts is None
        assert m.last_alert_ts is None

    def test_last_checkin_age_none_when_no_checkin(self):
        m = JobMetrics(job_name="backup")
        assert m.last_checkin_age_seconds is None

    def test_last_checkin_age_returns_elapsed(self):
        m = JobMetrics(job_name="backup")
        m.last_checkin_ts = time.time() - 30
        age = m.last_checkin_age_seconds
        assert age is not None
        assert 29 < age < 32


class TestMetricsCollector:
    def test_record_checkin_increments_count(self):
        c = MetricsCollector()
        c.record_checkin("job_a")
        c.record_checkin("job_a")
        assert c.get("job_a").total_checkins == 2

    def test_record_checkin_sets_timestamp(self):
        c = MetricsCollector()
        before = time.time()
        c.record_checkin("job_a")
        after = time.time()
        ts = c.get("job_a").last_checkin_ts
        assert before <= ts <= after

    def test_record_missed_increments_count(self):
        c = MetricsCollector()
        c.record_missed("job_b")
        c.record_missed("job_b")
        assert c.get("job_b").missed_runs == 2

    def test_get_returns_none_for_unknown_job(self):
        c = MetricsCollector()
        assert c.get("nonexistent") is None

    def test_all_returns_all_jobs(self):
        c = MetricsCollector()
        c.record_checkin("job_x")
        c.record_missed("job_y")
        result = c.all()
        assert set(result.keys()) == {"job_x", "job_y"}

    def test_reset_removes_job(self):
        c = MetricsCollector()
        c.record_checkin("job_a")
        c.reset("job_a")
        assert c.get("job_a") is None

    def test_reset_unknown_job_is_noop(self):
        c = MetricsCollector()
        c.reset("ghost")  # should not raise

    def test_summary_structure(self):
        c = MetricsCollector()
        c.record_checkin("job_a")
        c.record_missed("job_a")
        s = c.summary()
        assert "job_a" in s
        assert s["job_a"]["total_checkins"] == 1
        assert s["job_a"]["missed_runs"] == 1
        assert s["job_a"]["last_checkin_age_seconds"] is not None

    def test_summary_empty_when_no_jobs(self):
        c = MetricsCollector()
        assert c.summary() == {}
