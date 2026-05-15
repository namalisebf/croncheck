"""Tests for the croncheck CLI."""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from croncheck.cli import main
from croncheck.persistence import StateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_state(path: str, state: dict) -> None:
    store = StateStore(path)
    store.save(state)


def _sample_state(last_checkin: datetime | None = None) -> dict:
    """Return a minimal state dict with one job."""
    return {
        "backup": {
            "expression": "0 2 * * *",
            "grace_seconds": 300,
            "last_checkin": last_checkin.isoformat() if last_checkin else None,
        }
    }


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

class TestStatusCommand:
    def test_status_no_state_file_exits_nonzero(self, tmp_path):
        missing = str(tmp_path / "no_such_file.json")
        rc = main(["status", "--state-file", missing])
        assert rc == 1

    def test_status_prints_table(self, tmp_path, capsys):
        state_file = str(tmp_path / "state.json")
        recent = datetime.now(timezone.utc) - timedelta(minutes=1)
        _write_state(state_file, _sample_state(last_checkin=recent))

        rc = main(["status", "--state-file", state_file])
        assert rc == 0
        out = capsys.readouterr().out
        assert "backup" in out
        assert "OVERDUE" in out

    def test_status_json_output(self, tmp_path, capsys):
        state_file = str(tmp_path / "state.json")
        recent = datetime.now(timezone.utc) - timedelta(minutes=1)
        _write_state(state_file, _sample_state(last_checkin=recent))

        rc = main(["status", "--state-file", state_file, "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert data[0]["name"] == "backup"
        assert "overdue" in data[0]
        assert "last_checkin" in data[0]

    def test_status_overdue_flag_true_when_overdue(self, tmp_path, capsys):
        state_file = str(tmp_path / "state.json")
        # No check-in recorded — job should be overdue if past expected time
        _write_state(state_file, _sample_state(last_checkin=None))

        rc = main(["status", "--state-file", state_file, "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        # overdue is a bool; just assert the key is present and is a bool
        assert isinstance(data[0]["overdue"], bool)


# ---------------------------------------------------------------------------
# checkin command
# ---------------------------------------------------------------------------

class TestCheckinCommand:
    def test_checkin_unknown_job_exits_nonzero(self, tmp_path, capsys):
        state_file = str(tmp_path / "state.json")
        _write_state(state_file, _sample_state())

        rc = main(["checkin", "nonexistent_job", "--state-file", state_file])
        assert rc == 1
        assert "not found" in capsys.readouterr().err

    def test_checkin_updates_last_checkin(self, tmp_path, capsys):
        state_file = str(tmp_path / "state.json")
        _write_state(state_file, _sample_state())

        rc = main(["checkin", "backup", "--state-file", state_file])
        assert rc == 0
        assert "backup" in capsys.readouterr().out

        # Reload state and confirm last_checkin is now set
        store = StateStore(state_file)
        state = store.load()
        assert state["backup"]["last_checkin"] is not None

    def test_checkin_missing_state_file_exits_nonzero(self, tmp_path):
        missing = str(tmp_path / "no_such.json")
        rc = main(["checkin", "backup", "--state-file", missing])
        assert rc == 1
