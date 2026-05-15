"""Tests for WebhookBackend."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from croncheck.webhook import WebhookBackend


URL = "https://hooks.example.com/alert"


def _make_response(status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestWebhookBackend:
    def test_send_posts_json_payload(self):
        backend = WebhookBackend(url=URL)
        with patch("urllib.request.urlopen", return_value=_make_response()) as mock_open:
            backend.send("nightly-backup", "Job is overdue")

        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        assert req.full_url == URL
        assert req.method == "POST"
        body = json.loads(req.data.decode())
        assert body["job"] == "nightly-backup"
        assert body["message"] == "Job is overdue"

    def test_send_includes_extra_fields(self):
        backend = WebhookBackend(url=URL, extra_fields={"env": "prod", "team": "ops"})
        with patch("urllib.request.urlopen", return_value=_make_response()) as mock_open:
            backend.send("report-gen", "missed run")

        req = mock_open.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["env"] == "prod"
        assert body["team"] == "ops"

    def test_send_includes_extra_headers(self):
        backend = WebhookBackend(url=URL, extra_headers={"X-Token": "secret"})
        with patch("urllib.request.urlopen", return_value=_make_response()) as mock_open:
            backend.send("job", "msg")

        req = mock_open.call_args[0][0]
        assert req.get_header("X-token") == "secret"  # urllib capitalises first letter

    def test_http_error_is_logged_not_raised(self, caplog):
        backend = WebhookBackend(url=URL)
        exc = urllib.error.HTTPError(URL, 500, "Internal Server Error", {}, BytesIO())
        with patch("urllib.request.urlopen", side_effect=exc):
            backend.send("job", "msg")  # must not raise

        assert "500" in caplog.text

    def test_url_error_is_logged_not_raised(self, caplog):
        backend = WebhookBackend(url=URL)
        exc = urllib.error.URLError("connection refused")
        with patch("urllib.request.urlopen", side_effect=exc):
            backend.send("job", "msg")  # must not raise

        assert "connection refused" in caplog.text

    def test_unexpected_exception_is_logged_not_raised(self, caplog):
        backend = WebhookBackend(url=URL)
        with patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
            backend.send("job", "msg")  # must not raise

        assert "boom" in caplog.text

    def test_content_type_header_set(self):
        backend = WebhookBackend(url=URL)
        with patch("urllib.request.urlopen", return_value=_make_response()) as mock_open:
            backend.send("job", "msg")

        req = mock_open.call_args[0][0]
        assert req.get_header("Content-type") == "application/json"
