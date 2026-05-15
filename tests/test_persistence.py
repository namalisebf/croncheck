"""Tests for croncheck.persistence and croncheck.snapshot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from croncheck.persistence import StateStore, _deserialize_dt, _serialize_dt
from croncheck.snapshot import apply_state_to_registry, registry_to_state


UTC = timezone.utc
NOW = datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# _serialize_dt / _deserialize_dt
# ---------------------------------------------------------------------------

def test_serialize_none_returns_none():
    assert _serialize_dt(None) is None


def test_roundtrip_datetime():
    serialized = _serialize_dt(NOW)
    restored = _deserialize_dt(serialized)
    assert restored == NOW


def test_deserialize_none_returns_none():
    assert _deserialize_dt(None) is None


# ---------------------------------------------------------------------------
# StateStore
# ---------------------------------------------------------------------------

def test_load_returns_empty_dict_when_file_missing(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.load() == {}


def test_save_and_load_roundtrip(tmp_path):
    store = StateStore(tmp_path / "state.json")
    state = {
        "backup-job": {"last_checkin": NOW, "alerted": False},
        "report-job": {"last_checkin": None, "alerted": True},
    }
    store.save(state)
    loaded = store.load()
    assert loaded["backup-job"]["last_checkin"] == NOW
    assert loaded["backup-job"]["alerted"] is False
    assert loaded["report-job"]["last_checkin"] is None
    assert loaded["report-job"]["alerted"] is True


def test_save_creates_valid_json(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.save({"job": {"last_checkin": NOW, "alerted": False}})
    raw = json.loads((tmp_path / "state.json").read_text())
    assert "job" in raw
    assert isinstance(raw["job"]["last_checkin"], str)


def test_load_returns_empty_on_corrupt_file(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{not valid json", encoding="utf-8")
    store = StateStore(p)
    assert store.load() == {}


# ---------------------------------------------------------------------------
# snapshot helpers
# ---------------------------------------------------------------------------

def _make_registry(jobs, last_checkin, alerted):
    reg = MagicMock()
    reg.jobs = jobs
    reg.last_checkin = last_checkin
    reg.alerted = alerted
    return reg


def test_registry_to_state_captures_all_jobs():
    reg = _make_registry(
        jobs={"j1": object(), "j2": object()},
        last_checkin={"j1": NOW, "j2": None},
        alerted={"j1": True, "j2": False},
    )
    state = registry_to_state(reg)
    assert state["j1"]["last_checkin"] == NOW
    assert state["j1"]["alerted"] is True
    assert state["j2"]["alerted"] is False


def test_apply_state_skips_unknown_jobs():
    reg = _make_registry(
        jobs={"known": object()},
        last_checkin={},
        alerted={},
    )
    apply_state_to_registry({"unknown": {"last_checkin": NOW, "alerted": True}}, reg)
    assert "unknown" not in reg.last_checkin


def test_apply_state_restores_known_job():
    reg = _make_registry(
        jobs={"backup": object()},
        last_checkin={},
        alerted={},
    )
    apply_state_to_registry({"backup": {"last_checkin": NOW, "alerted": True}}, reg)
    assert reg.last_checkin["backup"] == NOW
    assert reg.alerted["backup"] is True
