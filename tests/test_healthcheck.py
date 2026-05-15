"""Tests for the HealthCheckServer and HealthCheckHandler."""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from croncheck.healthcheck import HealthCheckServer


def _make_mock_registry(jobs: list) -> MagicMock:
    registry = MagicMock()
    registry.all_jobs.return_value = jobs
    return registry


def _make_job(name: str, overdue: bool, last_checkin: datetime | None = None) -> MagicMock:
    job = MagicMock()
    job.name = name
    job.is_overdue.return_value = overdue
    job.last_checkin = last_checkin
    return job


FREE_PORT = 18765


@pytest.fixture()
def server_with_healthy_jobs():
    jobs = [_make_job("backup", overdue=False, last_checkin=datetime(2024, 1, 1, tzinfo=timezone.utc))]
    registry = _make_mock_registry(jobs)
    srv = HealthCheckServer(registry, port=FREE_PORT)
    srv.start()
    time.sleep(0.05)
    yield srv
    srv.stop()


@pytest.fixture()
def server_with_overdue_jobs():
    jobs = [
        _make_job("backup", overdue=True),
        _make_job("report", overdue=False),
    ]
    registry = _make_mock_registry(jobs)
    srv = HealthCheckServer(registry, port=FREE_PORT + 1)
    srv.start()
    time.sleep(0.05)
    yield srv
    srv.stop()


def _get(port: int, path: str = "/health") -> tuple[int, dict]:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url) as resp:
        return resp.status, json.loads(resp.read())


class TestHealthCheckServer:
    def test_healthy_response_status_ok(self, server_with_healthy_jobs):
        status, body = _get(FREE_PORT)
        assert status == 200
        assert body["status"] == "ok"

    def test_healthy_response_contains_jobs(self, server_with_healthy_jobs):
        _, body = _get(FREE_PORT)
        assert len(body["jobs"]) == 1
        assert body["jobs"][0]["name"] == "backup"
        assert body["jobs"][0]["overdue"] is False

    def test_overdue_response_status_degraded(self, server_with_overdue_jobs):
        _, body = _get(FREE_PORT + 1)
        assert body["status"] == "degraded"
        assert body["overdue_count"] == 1

    def test_unknown_path_returns_404(self, server_with_healthy_jobs):
        import urllib.error
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get(FREE_PORT, "/unknown")
        assert exc_info.value.code == 404

    def test_status_path_also_works(self, server_with_healthy_jobs):
        status, body = _get(FREE_PORT, "/status")
        assert status == 200
        assert "jobs" in body

    def test_last_checkin_serialised_as_iso(self, server_with_healthy_jobs):
        _, body = _get(FREE_PORT)
        assert body["jobs"][0]["last_checkin"] == "2024-01-01T00:00:00+00:00"
