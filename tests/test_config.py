"""Tests for croncheck.config module."""

import json
import os
import tempfile

import pytest

from croncheck.config import (
    AlertConfig,
    AppConfig,
    JobConfig,
    load_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(tmp_path, data: dict) -> str:
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return str(p)


# ---------------------------------------------------------------------------
# AppConfig defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_load_config_no_path_returns_defaults(self):
        cfg = load_config(path="")
        assert isinstance(cfg, AppConfig)
        assert cfg.check_interval_seconds == 60
        assert cfg.healthcheck_port == 8080
        assert cfg.jobs == []

    def test_load_config_missing_file_returns_defaults(self):
        cfg = load_config(path="/nonexistent/path/config.json")
        assert cfg.state_file == "/var/lib/croncheck/state.json"

    def test_env_var_ignored_when_missing(self, monkeypatch):
        monkeypatch.delenv("CRONCHECK_CONFIG", raising=False)
        cfg = load_config()
        assert isinstance(cfg, AppConfig)


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------

class TestJsonConfig:
    def test_top_level_fields_parsed(self, tmp_path):
        data = {
            "state_file": "/tmp/state.json",
            "check_interval_seconds": 30,
            "healthcheck_port": 9090,
            "healthcheck_host": "0.0.0.0",
        }
        cfg = load_config(_write_json(tmp_path, data))
        assert cfg.state_file == "/tmp/state.json"
        assert cfg.check_interval_seconds == 30
        assert cfg.healthcheck_port == 9090
        assert cfg.healthcheck_host == "0.0.0.0"

    def test_jobs_parsed(self, tmp_path):
        data = {
            "jobs": [
                {"name": "backup", "schedule": "0 2 * * *", "grace_seconds": 120},
                {"name": "report", "schedule": "0 8 * * 1"},
            ]
        }
        cfg = load_config(_write_json(tmp_path, data))
        assert len(cfg.jobs) == 2
        backup = cfg.jobs[0]
        assert isinstance(backup, JobConfig)
        assert backup.name == "backup"
        assert backup.grace_seconds == 120
        report = cfg.jobs[1]
        assert report.grace_seconds == 300  # default

    def test_alert_config_parsed(self, tmp_path):
        data = {
            "alert": {
                "backend": "email",
                "log_level": "ERROR",
                "email_to": ["ops@example.com"],
                "smtp_host": "mail.example.com",
                "smtp_port": 587,
            }
        }
        cfg = load_config(_write_json(tmp_path, data))
        assert isinstance(cfg.alert, AlertConfig)
        assert cfg.alert.backend == "email"
        assert cfg.alert.smtp_port == 587
        assert cfg.alert.email_to == ["ops@example.com"]

    def test_env_var_used_as_fallback(self, tmp_path, monkeypatch):
        data = {"check_interval_seconds": 15}
        path = _write_json(tmp_path, data)
        monkeypatch.setenv("CRONCHECK_CONFIG", path)
        cfg = load_config()  # no explicit path
        assert cfg.check_interval_seconds == 15

    def test_job_max_alerts_default(self, tmp_path):
        data = {"jobs": [{"name": "j", "schedule": "* * * * *"}]}
        cfg = load_config(_write_json(tmp_path, data))
        assert cfg.jobs[0].max_alerts == 5
