"""Tests for croncheck.escalation and croncheck.escalation_notifier."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from croncheck.escalation import EscalationPolicy, EscalationState
from croncheck.escalation_notifier import EscalatingNotifier


# ---------------------------------------------------------------------------
# EscalationPolicy
# ---------------------------------------------------------------------------

class TestEscalationPolicy:
    def _policy(self, warning_after=2, critical_after=5):
        return EscalationPolicy(warning_after=warning_after, critical_after=critical_after)

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            EscalationPolicy(warning_after=0, critical_after=5)
        with pytest.raises(ValueError):
            EscalationPolicy(warning_after=5, critical_after=3)

    def test_first_miss_is_normal(self):
        policy = self._policy()
        assert policy.record_miss("job1") == "normal"

    def test_second_miss_escalates_to_warning(self):
        policy = self._policy(warning_after=2)
        policy.record_miss("job1")
        level = policy.record_miss("job1")
        assert level == "warning"

    def test_fifth_miss_escalates_to_critical(self):
        policy = self._policy(critical_after=5)
        for _ in range(4):
            policy.record_miss("job1")
        level = policy.record_miss("job1")
        assert level == "critical"

    def test_checkin_resets_state(self):
        policy = self._policy()
        for _ in range(5):
            policy.record_miss("job1")
        policy.record_checkin("job1")
        assert policy.miss_count("job1") == 0
        assert policy.current_level("job1") == "normal"

    def test_checkin_no_reset_when_disabled(self):
        policy = EscalationPolicy(warning_after=2, critical_after=5, reset_on_checkin=False)
        for _ in range(5):
            policy.record_miss("job1")
        policy.record_checkin("job1")
        assert policy.miss_count("job1") == 5

    def test_independent_state_per_job(self):
        policy = self._policy()
        for _ in range(5):
            policy.record_miss("job_a")
        assert policy.current_level("job_b") == "normal"

    def test_miss_count_increments(self):
        policy = self._policy()
        policy.record_miss("j")
        policy.record_miss("j")
        assert policy.miss_count("j") == 2


# ---------------------------------------------------------------------------
# EscalatingNotifier
# ---------------------------------------------------------------------------

class TestEscalatingNotifier:
    def _make_notifier(self, overdue=True):
        job = MagicMock()
        job.name = "test_job"
        job.is_overdue.return_value = overdue

        registry = MagicMock()
        registry.all_jobs.return_value = [job]
        registry.last_checkin.return_value = None

        inner = MagicMock()
        policy = EscalationPolicy(warning_after=2, critical_after=5)
        notifier = EscalatingNotifier(inner, registry, policy)
        return notifier, inner, policy, job

    def test_overdue_job_calls_notify_failure(self):
        notifier, inner, _, _ = self._make_notifier(overdue=True)
        notifier.check_and_notify()
        inner.notify_failure.assert_called_once()

    def test_healthy_job_does_not_alert(self):
        notifier, inner, _, _ = self._make_notifier(overdue=False)
        notifier.check_and_notify()
        inner.notify_failure.assert_not_called()

    def test_escalation_level_passed_as_extra(self):
        notifier, inner, _, _ = self._make_notifier(overdue=True)
        notifier.check_and_notify()
        _, kwargs = inner.notify_failure.call_args
        assert kwargs.get("extra", {}).get("escalation_level") == "normal"

    def test_current_level_exposed(self):
        notifier, _, policy, _ = self._make_notifier(overdue=True)
        notifier.check_and_notify()
        assert notifier.current_level("test_job") in ("normal", "warning", "critical")

    def test_record_checkin_resets_policy(self):
        notifier, _, policy, _ = self._make_notifier(overdue=True)
        for _ in range(5):
            notifier.check_and_notify()
        notifier.record_checkin("test_job")
        assert policy.miss_count("test_job") == 0
