"""Periodic digest sender: fires a summary alert on a configurable interval."""

from __future__ import annotations

import logging
import threading
from datetime import timedelta
from typing import Optional

from croncheck.alerts import AlertBackend
from croncheck.digest import DigestReport, build_digest
from croncheck.registry import JobRegistry

logger = logging.getLogger(__name__)


class DigestSender:
    """Sends a periodic digest of all job statuses via the configured backend."""

    def __init__(
        self,
        registry: JobRegistry,
        backend: AlertBackend,
        interval: timedelta = timedelta(hours=1),
    ) -> None:
        self._registry = registry
        self._backend = backend
        self._interval = interval
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin scheduling periodic digests."""
        with self._lock:
            if self._running:
                return
            self._running = True
        self._schedule_next()
        logger.info("DigestSender started (interval=%s)", self._interval)

    def stop(self) -> None:
        """Cancel any pending digest timer."""
        with self._lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        logger.info("DigestSender stopped")

    def send_now(self) -> DigestReport:
        """Build and dispatch a digest immediately; returns the report."""
        report = build_digest(self._registry)
        subject = (
            f"croncheck digest: {report.overdue_count} overdue / "
            f"{len(report.entries)} jobs"
        )
        self._backend.send(subject, report.format_text())
        logger.debug("Digest sent: %d entries", len(report.entries))
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _schedule_next(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._timer = threading.Timer(
                self._interval.total_seconds(), self._fire
            )
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        try:
            self.send_now()
        except Exception:
            logger.exception("DigestSender: error while sending digest")
        self._schedule_next()
