"""Persistence layer for croncheck — saves and loads job check-in state."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_DATETIME_FMT = "%Y-%m-%dT%H:%M:%S.%f+00:00"


def _serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime(_DATETIME_FMT)


def _deserialize_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.strptime(value, _DATETIME_FMT).replace(tzinfo=timezone.utc)


class StateStore:
    """Persists job last_checkin and alerted state to a JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Dict[str, dict]:
        """Return stored state dict keyed by job name."""
        if not self.path.exists():
            return {}
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            for entry in data.values():
                entry["last_checkin"] = _deserialize_dt(entry.get("last_checkin"))
            return data
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to load state from %s: %s", self.path, exc)
            return {}

    def save(self, state: Dict[str, dict]) -> None:
        """Persist state dict to disk atomically."""
        serializable = {}
        for name, entry in state.items():
            serializable[name] = {
                "last_checkin": _serialize_dt(entry.get("last_checkin")),
                "alerted": entry.get("alerted", False),
            }
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            logger.error("Failed to save state to %s: %s", self.path, exc)
