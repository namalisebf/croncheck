"""Webhook alert backend for croncheck."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from croncheck.alerts import AlertBackend

logger = logging.getLogger(__name__)


@dataclass
class WebhookBackend(AlertBackend):
    """Send alert notifications to an HTTP webhook endpoint."""

    url: str
    timeout: int = 10
    extra_headers: Dict[str, str] = field(default_factory=dict)
    # Optional static payload fields merged into every request body.
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def send(self, job_name: str, message: str) -> None:
        """POST a JSON payload to the configured webhook URL."""
        payload: Dict[str, Any] = {
            "job": job_name,
            "message": message,
            **self.extra_fields,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        req = urllib.request.Request(
            self.url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                logger.debug(
                    "Webhook delivered for job '%s': HTTP %s", job_name, status
                )
        except urllib.error.HTTPError as exc:
            logger.error(
                "Webhook HTTP error for job '%s': %s %s", job_name, exc.code, exc.reason
            )
        except urllib.error.URLError as exc:
            logger.error(
                "Webhook connection error for job '%s': %s", job_name, exc.reason
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Unexpected error sending webhook for job '%s': %s", job_name, exc
            )
