"""Correlation ID support for linking related alert events across backends."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Optional


_local = threading.local()


def current_correlation_id() -> Optional[str]:
    """Return the correlation ID bound to the current thread, or None."""
    return getattr(_local, "correlation_id", None)


def set_correlation_id(cid: str) -> None:
    """Bind a correlation ID to the current thread."""
    _local.correlation_id = cid


def clear_correlation_id() -> None:
    """Remove any correlation ID bound to the current thread."""
    _local.correlation_id = None


def new_correlation_id() -> str:
    """Generate a fresh correlation ID and bind it to the current thread."""
    cid = uuid.uuid4().hex
    set_correlation_id(cid)
    return cid


class CorrelationContext:
    """Context manager that sets a correlation ID for the duration of a block.

    If *cid* is omitted a new UUID is generated automatically.
    The previous value (if any) is restored on exit.
    """

    def __init__(self, cid: Optional[str] = None) -> None:
        self._cid = cid or uuid.uuid4().hex
        self._previous: Optional[str] = None

    # expose the id so callers can read it
    @property
    def correlation_id(self) -> str:
        return self._cid

    def __enter__(self) -> "CorrelationContext":
        self._previous = current_correlation_id()
        set_correlation_id(self._cid)
        return self

    def __exit__(self, *_exc) -> None:
        if self._previous is None:
            clear_correlation_id()
        else:
            set_correlation_id(self._previous)


@dataclass
class CorrelatedAlert:
    """Wraps an alert payload with a correlation ID."""

    job_name: str
    alert_type: str
    message: str
    correlation_id: str = field(default_factory=lambda: current_correlation_id() or uuid.uuid4().hex)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "alert_type": self.alert_type,
            "message": self.message,
            "correlation_id": self.correlation_id,
        }
