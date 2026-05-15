"""Alert backends for croncheck notifications."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

logger = logging.getLogger(__name__)


class AlertBackend(Protocol):
    """Protocol that all alert backends must satisfy."""

    def send(self, subject: str, body: str) -> None:
        ...


@dataclass
class LoggingBackend:
    """Simple backend that logs alerts using Python's logging module."""

    level: int = logging.WARNING

    def send(self, subject: str, body: str) -> None:
        logger.log(self.level, "[croncheck] %s — %s", subject, body)


@dataclass
class EmailBackend:
    """SMTP-based email alert backend."""

    smtp_host: str
    smtp_port: int
    sender: str
    recipients: list[str]
    username: str = ""
    password: str = ""
    use_tls: bool = True

    def send(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(msg)
            logger.info("Alert email sent to %s", self.recipients)
        except smtplib.SMTPException as exc:
            logger.error("Failed to send alert email: %s", exc)


@dataclass
class MultiBackend:
    """Fan-out backend that forwards alerts to multiple backends."""

    backends: list[AlertBackend] = field(default_factory=list)

    def send(self, subject: str, body: str) -> None:
        for backend in self.backends:
            try:
                backend.send(subject, body)
            except Exception as exc:  # noqa: BLE001
                logger.error("Backend %r failed: %s", backend, exc)
