"""Audit log for cron job state transitions and alert events."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """A single audit log entry."""

    timestamp: datetime
    job_name: str
    event_type: str  # 'checkin', 'overdue', 'alert_sent', 'alert_suppressed', 'recovered'
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "job_name": self.job_name,
            "event_type": self.event_type,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            job_name=data["job_name"],
            event_type=data["event_type"],
            detail=data.get("detail", ""),
        )


class AuditLog:
    """Appends audit events to a JSONL file and exposes recent history."""

    def __init__(self, path: Optional[Path] = None, max_memory: int = 500):
        self._path = path
        self._max_memory = max_memory
        self._events: List[AuditEvent] = []

    def record(self, job_name: str, event_type: str, detail: str = "") -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            job_name=job_name,
            event_type=event_type,
            detail=detail,
        )
        self._events.append(event)
        if len(self._events) > self._max_memory:
            self._events = self._events[-self._max_memory :]
        if self._path is not None:
            self._append_to_file(event)
        logger.debug("audit: %s %s %s", event_type, job_name, detail)
        return event

    def _append_to_file(self, event: AuditEvent) -> None:
        try:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict()) + "\n")
        except OSError as exc:
            logger.warning("Failed to write audit log: %s", exc)

    def recent(self, n: int = 50, job_name: Optional[str] = None) -> List[AuditEvent]:
        events = self._events
        if job_name is not None:
            events = [e for e in events if e.job_name == job_name]
        return events[-n:]

    def load_from_file(self) -> None:
        """Populate in-memory events from the JSONL file (called at startup)."""
        if self._path is None or not Path(self._path).exists():
            return
        loaded: List[AuditEvent] = []
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        loaded.append(AuditEvent.from_dict(json.loads(line)))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load audit log: %s", exc)
            return
        self._events = loaded[-self._max_memory :]
