"""Retry policy for alert delivery with exponential backoff."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behaviour."""

    max_attempts: int = 3
    base_delay: float = 1.0   # seconds
    backoff_factor: float = 2.0
    max_delay: float = 30.0

    def delay_for(self, attempt: int) -> float:
        """Return the sleep duration before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


@dataclass
class RetryState:
    """Mutable state tracked per-job for retry accounting."""

    attempts: int = 0
    last_error: Optional[str] = None
    succeeded: bool = False


class RetryDispatcher:
    """Wraps an alert backend and retries on transient failures."""

    def __init__(self, backend, policy: Optional[RetryPolicy] = None) -> None:
        self._backend = backend
        self._policy = policy or RetryPolicy()

    def send(self, job_name: str, message: str) -> bool:
        """Attempt delivery, retrying up to *max_attempts* times.

        Returns True if delivery succeeded, False otherwise.
        """
        policy = self._policy
        state = RetryState()

        for attempt in range(policy.max_attempts):
            delay = policy.delay_for(attempt)
            if delay > 0:
                logger.debug(
                    "retry: waiting %.1fs before attempt %d for job '%s'",
                    delay, attempt + 1, job_name,
                )
                time.sleep(delay)

            try:
                self._backend.send(job_name, message)
                state.attempts = attempt + 1
                state.succeeded = True
                logger.debug(
                    "retry: delivery succeeded on attempt %d for job '%s'",
                    state.attempts, job_name,
                )
                return True
            except Exception as exc:  # noqa: BLE001
                state.attempts = attempt + 1
                state.last_error = str(exc)
                logger.warning(
                    "retry: attempt %d/%d failed for job '%s': %s",
                    state.attempts, policy.max_attempts, job_name, exc,
                )

        logger.error(
            "retry: all %d attempts exhausted for job '%s'; last error: %s",
            policy.max_attempts, job_name, state.last_error,
        )
        return False
