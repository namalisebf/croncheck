"""Tests for croncheck.audit and croncheck.audit_middleware."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from croncheck.audit import AuditEvent, AuditLog
from croncheck.audit_middleware import AuditingNotifier


# ---------------------------------------------------------------------------
# AuditEvent
# ---------------------------------------------------------------------------

class TestAuditEvent:
    def test_to_dict_round_trip(self):
        now = datetime.now(timezone.utc)
        event = AuditEvent(timestamp=now, job_name="backup", event_type="checkin", detail="ok")
        d = event.to_dict()
        restored = AuditEvent.from_dict(d)
        assert restored.job_name == "backup"
        assert restored.event_type == "checkin"
        assert restored.detail == "ok"
        assert restored.timestamp == now

    def test_from_dict_missing_detail_defaults_empty(self):
        d = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_name": "x",
            "event_type": "overdue",
        }
        event = AuditEvent.from_dict(d)
        assert event.detail == ""


# ---------------------------------------------------------------------------
# AuditLog (in-memory)
# ---------------------------------------------------------------------------

class TestAuditLogMemory:
    def test_record_stores_event(self):
        log = AuditLog()
        log.record("myjob", "checkin")
        assert len(log.recent()) == 1
        assert log.recent()[0].job_name == "myjob"

    def test_recent_filters_by_job(self):
        log = AuditLog()
        log.record("job_a", "checkin")
        log.record("job_b", "overdue")
        assert len(log.recent(job_name="job_a")) == 1

    def test_max_memory_trims_old_events(self):
        log = AuditLog(max_memory=5)
        for i in range(10):
            log.record(f"job_{i}", "checkin")
        assert len(log.recent(n=100)) == 5

    def test_recent_respects_n(self):
        log = AuditLog()
        for i in range(20):
            log.record("job", "checkin")
        assert len(log.recent(n=5)) == 5


# ---------------------------------------------------------------------------
# AuditLog (file)
# ---------------------------------------------------------------------------

class TestAuditLogFile:
    def test_appends_jsonl_to_file(self, tmp_path):
        p = tmp_path / "audit.jsonl"
        log = AuditLog(path=p)
        log.record("job1", "alert_sent", "via email")
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event_type"] == "alert_sent"

    def test_load_from_file_populates_memory(self, tmp_path):
        p = tmp_path / "audit.jsonl"
        log = AuditLog(path=p)
        log.record("job1", "checkin")
        log.record("job2", "overdue")

        log2 = AuditLog(path=p)
        log2.load_from_file()
        assert len(log2.recent(n=100)) == 2

    def test_load_missing_file_is_noop(self, tmp_path):
        log = AuditLog(path=tmp_path / "missing.jsonl")
        log.load_from_file()  # should not raise
        assert log.recent() == []

    def test_write_failure_does_not_raise(self, tmp_path):
        p = tmp_path / "subdir" / "audit.jsonl"  # subdir does not exist
        log = AuditLog(path=p)
        log.record("job", "checkin")  # OSError swallowed


# ---------------------------------------------------------------------------
# AuditingNotifier
# ---------------------------------------------------------------------------

class TestAuditingNotifier:
    def _make_notifier_and_registry(self, overdue_names):
        mock_notifier = MagicMock()
        mock_registry = MagicMock()
        jobs = {}
        for name in overdue_names:
            job = MagicMock()
            job.is_overdue.return_value = True
            jobs[name] = job
        mock_registry.jobs = jobs
        return mock_notifier, mock_registry

    def test_overdue_event_recorded(self):
        notifier, registry = self._make_notifier_and_registry(["backup"])
        audit = AuditLog()
        an = AuditingNotifier(notifier, audit, registry)
        an.check_and_notify()
        events = audit.recent(job_name="backup")
        assert any(e.event_type == "overdue" for e in events)

    def test_recovered_event_recorded(self):
        notifier, registry = self._make_notifier_and_registry(["backup"])
        audit = AuditLog()
        an = AuditingNotifier(notifier, audit, registry)
        an.check_and_notify()  # becomes overdue

        registry.jobs["backup"].is_overdue.return_value = False
        an.check_and_notify()  # recovers
        events = audit.recent(job_name="backup")
        assert any(e.event_type == "recovered" for e in events)

    def test_record_checkin_writes_event(self):
        notifier, registry = self._make_notifier_and_registry([])
        audit = AuditLog()
        an = AuditingNotifier(notifier, audit, registry)
        an.record_checkin("myjob")
        assert audit.recent(job_name="myjob")[0].event_type == "checkin"

    def test_record_alert_sent(self):
        notifier, registry = self._make_notifier_and_registry([])
        audit = AuditLog()
        an = AuditingNotifier(notifier, audit, registry)
        an.record_alert_sent("myjob", "EmailBackend")
        e = audit.recent(job_name="myjob")[0]
        assert e.event_type == "alert_sent"
        assert "EmailBackend" in e.detail
