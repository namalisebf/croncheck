"""HTTP healthcheck endpoint for croncheck daemon status reporting."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from croncheck.registry import JobRegistry

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that exposes job registry status as JSON."""

    registry: "JobRegistry"  # injected by HealthCheckServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/health", "/status"):
            self.send_response(404)
            self.end_headers()
            return

        jobs = self.registry.all_jobs()
        payload = {
            "status": "ok",
            "jobs": [
                {
                    "name": job.name,
                    "overdue": job.is_overdue(),
                    "last_checkin": (
                        job.last_checkin.isoformat() if job.last_checkin else None
                    ),
                }
                for job in jobs
            ],
        }
        overdue_count = sum(1 for job in jobs if job.is_overdue())
        if overdue_count:
            payload["status"] = "degraded"
            payload["overdue_count"] = overdue_count

        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D102
        logger.debug(fmt, *args)


class HealthCheckServer:
    """Threaded HTTP server that serves healthcheck data for the daemon."""

    def __init__(self, registry: "JobRegistry", host: str = "127.0.0.1", port: int = 8765) -> None:
        self.registry = registry
        self.host = host
        self.port = port
        self._server: HTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the healthcheck HTTP server in a background thread."""
        handler = type(
            "_Handler",
            (HealthCheckHandler,),
            {"registry": self.registry},
        )
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Healthcheck server listening on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Shut down the healthcheck HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        logger.info("Healthcheck server stopped")
