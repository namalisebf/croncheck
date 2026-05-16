"""Escalation policy: upgrade alert severity after repeated missed check-ins."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class EscalationState:
    """Tracks escalation state for a single job."""
    consecutive_misses: int = 0
    last_escalated_at: Optional[float] = None
    current_level: int = 0  # 0=normal, 1=warning, 2=critical


class EscalationPolicy:
    """Determines alert level based on consecutive missed check-ins.

    Args:
        warning_after:  number of consecutive misses before WARNING level.
        critical_after: number of consecutive misses before CRITICAL level.
        reset_on_checkin: whether a successful check-in resets the counter.
    """

    LEVELS = ("normal", "warning", "critical")

    def __init__(
        self,
        warning_after: int = 2,
        critical_after: int = 5,
        reset_on_checkin: bool = True,
    ) -> None:
        if warning_after < 1 or critical_after <= warning_after:
            raise ValueError(
                "critical_after must be greater than warning_after >= 1"
            )
        self.warning_after = warning_after
        self.critical_after = critical_after
        self.reset_on_checkin = reset_on_checkin
        self._states: Dict[str, EscalationState] = {}

    def _state(self, job_name: str) -> EscalationState:
        if job_name not in self._states:
            self._states[job_name] = EscalationState()
        return self._states[job_name]

    def record_miss(self, job_name: str) -> str:
        """Increment miss counter and return the current level label."""
        state = self._state(job_name)
        state.consecutive_misses += 1
        state.last_escalated_at = time.time()

        if state.consecutive_misses >= self.critical_after:
            state.current_level = 2
        elif state.consecutive_misses >= self.warning_after:
            state.current_level = 1
        else:
            state.current_level = 0

        return self.LEVELS[state.current_level]

    def record_checkin(self, job_name: str) -> None:
        """Reset escalation state on a successful check-in (if configured)."""
        if self.reset_on_checkin and job_name in self._states:
            self._states[job_name] = EscalationState()

    def current_level(self, job_name: str) -> str:
        """Return the current escalation level label without mutating state."""
        state = self._state(job_name)
        return self.LEVELS[state.current_level]

    def miss_count(self, job_name: str) -> int:
        """Return the current consecutive miss count for a job."""
        return self._state(job_name).consecutive_misses
