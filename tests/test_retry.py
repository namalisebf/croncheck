"""Tests for croncheck.retry."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call, patch

from croncheck.retry import RetryDispatcher, RetryPolicy


class TestRetryPolicy:
    def test_delay_for_first_attempt_is_zero(self):
        policy = RetryPolicy(base_delay=2.0, backoff_factor=2.0)
        assert policy.delay_for(0) == 0.0

    def test_delay_increases_exponentially(self):
        policy = RetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=100.0)
        assert policy.delay_for(1) == 1.0
        assert policy.delay_for(2) == 2.0
        assert policy.delay_for(3) == 4.0

    def test_delay_capped_at_max(self):
        policy = RetryPolicy(base_delay=10.0, backoff_factor=10.0, max_delay=15.0)
        assert policy.delay_for(3) == 15.0


class TestRetryDispatcher:
    def _make_dispatcher(self, backend, **policy_kwargs):
        policy = RetryPolicy(**policy_kwargs) if policy_kwargs else RetryPolicy()
        return RetryDispatcher(backend, policy)

    def test_success_on_first_attempt_returns_true(self):
        backend = MagicMock()
        dispatcher = self._make_dispatcher(backend, max_attempts=3)
        result = dispatcher.send("my-job", "overdue")
        assert result is True
        backend.send.assert_called_once_with("my-job", "overdue")

    def test_retries_on_failure_then_succeeds(self):
        backend = MagicMock()
        backend.send.side_effect = [RuntimeError("timeout"), None]
        dispatcher = self._make_dispatcher(
            backend, max_attempts=3, base_delay=0.0
        )
        with patch("croncheck.retry.time.sleep"):
            result = dispatcher.send("job", "msg")
        assert result is True
        assert backend.send.call_count == 2

    def test_all_attempts_fail_returns_false(self):
        backend = MagicMock()
        backend.send.side_effect = RuntimeError("network error")
        dispatcher = self._make_dispatcher(
            backend, max_attempts=3, base_delay=0.0
        )
        with patch("croncheck.retry.time.sleep"):
            result = dispatcher.send("job", "msg")
        assert result is False
        assert backend.send.call_count == 3

    def test_no_retry_when_max_attempts_one(self):
        backend = MagicMock()
        backend.send.side_effect = RuntimeError("fail")
        dispatcher = self._make_dispatcher(backend, max_attempts=1, base_delay=0.0)
        result = dispatcher.send("job", "msg")
        assert result is False
        backend.send.assert_called_once()

    def test_sleep_called_with_correct_delays(self):
        backend = MagicMock()
        backend.send.side_effect = [RuntimeError(), RuntimeError(), None]
        policy = RetryPolicy(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
        dispatcher = RetryDispatcher(backend, policy)
        with patch("croncheck.retry.time.sleep") as mock_sleep:
            dispatcher.send("job", "msg")
        # attempt 0 → no sleep; attempt 1 → 1.0s; attempt 2 → 2.0s
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])
        assert mock_sleep.call_count == 2
