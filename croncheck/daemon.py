"""Background daemon loop that periodically invokes the Notifier."""

from __future__ import annotations

import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from croncheck.notifier import Notifier

logger = logging.getLogger(__name__)


@dataclass
class CronCheckDaemon:
    """Runs the notifier on a fixed interval until stopped."""

    notifier: Notifier
    interval: float = 60.0  # seconds between checks

    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)

    def start(self, *, block: bool = False) -> None:
        """Start the daemon. If block=True, run in the calling thread."""
        self._stop_event.clear()
        if block:
            self._run()
        else:
            self._thread = threading.Thread(
                target=self._run, name="croncheck-daemon", daemon=True
            )
            self._thread.start()
            logger.info("CronCheck daemon started (interval=%.1fs)", self.interval)

    def stop(self) -> None:
        """Signal the daemon to stop and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval + 5)
        logger.info("CronCheck daemon stopped.")

    def _run(self) -> None:
        logger.info("Daemon loop running.")
        while not self._stop_event.is_set():
            try:
                alerted = self.notifier.check_and_notify()
                if alerted:
                    logger.debug("Alerted jobs this cycle: %s", alerted)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error during check cycle: %s", exc)
            self._stop_event.wait(timeout=self.interval)

    # ------------------------------------------------------------------
    # Convenience: handle SIGTERM / SIGINT gracefully
    # ------------------------------------------------------------------
    def install_signal_handlers(self) -> None:
        """Register OS signal handlers to stop the daemon cleanly."""

        def _handler(signum: int, _frame: object) -> None:
            logger.info("Received signal %d, stopping daemon.", signum)
            self.stop()

        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)
