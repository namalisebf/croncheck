"""Tests for croncheck.correlation and croncheck.correlation_middleware."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from croncheck.correlation import (
    CorrelatedAlert,
    CorrelationContext,
    clear_correlation_id,
    current_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from croncheck.correlation_middleware import CorrelatingNotifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notifier_and_registry():
    inner = MagicMock()
    registry = MagicMock()
    notifier = CorrelatingNotifier(inner, registry)
    return notifier, inner, registry


# ---------------------------------------------------------------------------
# CorrelationContext
# ---------------------------------------------------------------------------

class TestCorrelationContext:
    def setup_method(self):
        clear_correlation_id()

    def test_sets_id_within_block(self):
        with CorrelationContext("abc123") as ctx:
            assert current_correlation_id() == "abc123"
            assert ctx.correlation_id == "abc123"

    def test_clears_id_after_block(self):
        with CorrelationContext("abc123"):
            pass
        assert current_correlation_id() is None

    def test_restores_previous_id(self):
        set_correlation_id("outer")
        with CorrelationContext("inner"):
            assert current_correlation_id() == "inner"
        assert current_correlation_id() == "outer"

    def test_auto_generates_id_when_omitted(self):
        with CorrelationContext() as ctx:
            assert len(ctx.correlation_id) == 32  # uuid4 hex

    def test_nested_contexts_restore_correctly(self):
        with CorrelationContext("first") as c1:
            with CorrelationContext("second") as c2:
                assert current_correlation_id() == "second"
            assert current_correlation_id() == "first"


# ---------------------------------------------------------------------------
# Thread isolation
# ---------------------------------------------------------------------------

def test_correlation_id_is_thread_local():
    results = {}

    def worker(name, cid):
        set_correlation_id(cid)
        import time; time.sleep(0.02)
        results[name] = current_correlation_id()

    t1 = threading.Thread(target=worker, args=("t1", "id-t1"))
    t2 = threading.Thread(target=worker, args=("t2", "id-t2"))
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert results["t1"] == "id-t1"
    assert results["t2"] == "id-t2"


# ---------------------------------------------------------------------------
# CorrelatedAlert
# ---------------------------------------------------------------------------

class TestCorrelatedAlert:
    def test_to_dict_contains_all_fields(self):
        alert = CorrelatedAlert("backup", "overdue", "Job is overdue", "cid-99")
        d = alert.to_dict()
        assert d["job_name"] == "backup"
        assert d["alert_type"] == "overdue"
        assert d["correlation_id"] == "cid-99"

    def test_uses_thread_local_id_by_default(self):
        set_correlation_id("thread-cid")
        alert = CorrelatedAlert("backup", "overdue", "msg")
        assert alert.correlation_id == "thread-cid"
        clear_correlation_id()


# ---------------------------------------------------------------------------
# CorrelatingNotifier
# ---------------------------------------------------------------------------

class TestCorrelatingNotifier:
    def setup_method(self):
        clear_correlation_id()

    def test_check_and_notify_returns_correlation_id(self):
        notifier, inner, _ = _make_notifier_and_registry()
        cid = notifier.check_and_notify()
        assert isinstance(cid, str) and len(cid) == 32
        inner.check_and_notify.assert_called_once()

    def test_each_sweep_gets_unique_id(self):
        notifier, _, _ = _make_notifier_and_registry()
        ids = {notifier.check_and_notify() for _ in range(5)}
        assert len(ids) == 5

    def test_notify_failure_reuses_active_id(self):
        notifier, inner, _ = _make_notifier_and_registry()
        job = MagicMock()
        set_correlation_id("active-cid")
        cid = notifier.notify_failure(job, "overdue")
        assert cid == "active-cid"
        inner.notify_failure.assert_called_once_with(job, "overdue")

    def test_notify_failure_creates_id_when_none_set(self):
        notifier, inner, _ = _make_notifier_and_registry()
        job = MagicMock()
        cid = notifier.notify_failure(job, "overdue")
        assert isinstance(cid, str) and len(cid) == 32
        inner.notify_failure.assert_called_once()

    def test_id_cleared_after_check_and_notify(self):
        notifier, _, _ = _make_notifier_and_registry()
        notifier.check_and_notify()
        assert current_correlation_id() is None
