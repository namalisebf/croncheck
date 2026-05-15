"""Tests for alert backends."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from croncheck.alerts import EmailBackend, LoggingBackend, MultiBackend


class TestLoggingBackend:
    def test_send_logs_at_configured_level(self, caplog):
        backend = LoggingBackend(level=logging.WARNING)
        with caplog.at_level(logging.WARNING, logger="croncheck.alerts"):
            backend.send("Test subject", "Test body")
        assert "Test subject" in caplog.text
        assert "Test body" in caplog.text

    def test_default_level_is_warning(self):
        backend = LoggingBackend()
        assert backend.level == logging.WARNING


class TestMultiBackend:
    def test_sends_to_all_backends(self):
        b1 = MagicMock()
        b2 = MagicMock()
        multi = MultiBackend(backends=[b1, b2])
        multi.send("subj", "body")
        b1.send.assert_called_once_with("subj", "body")
        b2.send.assert_called_once_with("subj", "body")

    def test_continues_if_one_backend_fails(self):
        b1 = MagicMock(side_effect=RuntimeError("boom"))
        b2 = MagicMock()
        multi = MultiBackend(backends=[b1, b2])
        multi.send("subj", "body")  # should not raise
        b2.send.assert_called_once_with("subj", "body")

    def test_empty_backends_no_error(self):
        multi = MultiBackend()
        multi.send("subj", "body")  # should not raise


class TestEmailBackend:
    def _make_backend(self) -> EmailBackend:
        return EmailBackend(
            smtp_host="localhost",
            smtp_port=587,
            sender="croncheck@example.com",
            recipients=["ops@example.com"],
        )

    def test_send_calls_smtp(self):
        backend = self._make_backend()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__.return_value = mock_server
            backend.send("Alert", "Something went wrong")
            mock_server.send_message.assert_called_once()

    def test_send_logs_error_on_smtp_exception(self, caplog):
        backend = self._make_backend()
        with patch("smtplib.SMTP", side_effect=Exception("conn refused")):
            with caplog.at_level(logging.ERROR, logger="croncheck.alerts"):
                backend.send("Alert", "body")  # should not raise
        assert "Failed" in caplog.text or "conn refused" in caplog.text
