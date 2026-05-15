"""Configuration loading for croncheck daemon."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ImportError:  # Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        tomllib = None  # type: ignore[assignment]

import json


@dataclass
class JobConfig:
    name: str
    schedule: str
    grace_seconds: int = 300
    alert_cooldown_seconds: int = 3600
    max_alerts: int = 5


@dataclass
class AlertConfig:
    backend: str = "logging"  # logging | email | multi
    log_level: str = "WARNING"
    email_to: List[str] = field(default_factory=list)
    email_from: str = "croncheck@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25


@dataclass
class AppConfig:
    state_file: str = "/var/lib/croncheck/state.json"
    check_interval_seconds: int = 60
    healthcheck_port: int = 8080
    healthcheck_host: str = "127.0.0.1"
    alert: AlertConfig = field(default_factory=AlertConfig)
    jobs: List[JobConfig] = field(default_factory=list)


def _parse_jobs(raw_jobs: List[Dict[str, Any]]) -> List[JobConfig]:
    result = []
    for entry in raw_jobs:
        result.append(
            JobConfig(
                name=entry["name"],
                schedule=entry["schedule"],
                grace_seconds=int(entry.get("grace_seconds", 300)),
                alert_cooldown_seconds=int(entry.get("alert_cooldown_seconds", 3600)),
                max_alerts=int(entry.get("max_alerts", 5)),
            )
        )
    return result


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        backend=raw.get("backend", "logging"),
        log_level=raw.get("log_level", "WARNING"),
        email_to=raw.get("email_to", []),
        email_from=raw.get("email_from", "croncheck@localhost"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
    )


def load_config(path: Optional[str] = None) -> AppConfig:
    """Load configuration from a TOML or JSON file.

    Falls back to defaults when no path is given or the file is absent.
    """
    if path is None:
        path = os.environ.get("CRONCHECK_CONFIG", "")

    if not path or not os.path.exists(path):
        return AppConfig()

    with open(path, "rb") as fh:
        raw_bytes = fh.read()

    if path.endswith(".json"):
        raw: Dict[str, Any] = json.loads(raw_bytes)
    else:
        if tomllib is None:  # pragma: no cover
            raise RuntimeError(
                "TOML support requires Python 3.11+ or 'tomli' package."
            )
        raw = tomllib.loads(raw_bytes.decode())

    alert_cfg = _parse_alert(raw.get("alert", {}))
    jobs_cfg = _parse_jobs(raw.get("jobs", []))

    return AppConfig(
        state_file=raw.get("state_file", "/var/lib/croncheck/state.json"),
        check_interval_seconds=int(raw.get("check_interval_seconds", 60)),
        healthcheck_port=int(raw.get("healthcheck_port", 8080)),
        healthcheck_host=raw.get("healthcheck_host", "127.0.0.1"),
        alert=alert_cfg,
        jobs=jobs_cfg,
    )
