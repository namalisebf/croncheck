"""Notifier middleware that enriches alerts with escalation level."""
from __future__ import annotations

from croncheck.escalation import EscalationPolicy
from croncheck.notifier import Notifier
from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob


class EscalatingNotifier:
    """Wraps a Notifier and upgrades alert messages based on escalation level.

    Args:
        inner:    underlying Notifier to delegate actual dispatch.
        registry: job registry used for overdue checks.
        policy:   EscalationPolicy instance (created with defaults if omitted).
    """

    def __init__(
        self,
        inner: Notifier,
        registry: JobRegistry,
        policy: EscalationPolicy | None = None,
    ) -> None:
        self._inner = inner
        self._registry = registry
        self._policy = policy or EscalationPolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_notify(self) -> None:
        """Check all jobs; escalate level for each overdue job before alerting."""
        for job in self._registry.all_jobs():
            if job.is_overdue(self._registry.last_checkin(job.name)):
                level = self._policy.record_miss(job.name)
                self._inner.notify_failure(
                    job,
                    extra={"escalation_level": level},
                )
            else:
                # Successful implicit check-in (job is on time)
                self._policy.record_checkin(job.name)

    def record_checkin(self, job_name: str) -> None:
        """Propagate an explicit check-in and reset escalation state."""
        self._policy.record_checkin(job_name)

    def current_level(self, job_name: str) -> str:
        """Expose the current escalation level for a job (e.g. for health API)."""
        return self._policy.current_level(job_name)
