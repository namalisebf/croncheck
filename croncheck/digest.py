"""Digest reporter: aggregates job statuses into a periodic summary alert."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from croncheck.registry import JobRegistry

logger = logging.getLogger(__name__)


@dataclass
class DigestEntry:
    job_name: str
    is_overdue: bool
    last_checkin: Optional[datetime]
    next_run: datetime

    def status_label(self) -> str:
        return "OVERDUE" if self.is_overdue else "OK"


@dataclass
class DigestReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entries: List[DigestEntry] = field(default_factory=list)

    @property
    def overdue_count(self) -> int:
        return sum(1 for e in self.entries if e.is_overdue)

    @property
    def healthy_count(self) -> int:
        return len(self.entries) - self.overdue_count

    def format_text(self) -> str:
        lines = [
            f"croncheck digest — {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total: {len(self.entries)}  Healthy: {self.healthy_count}  Overdue: {self.overdue_count}",
            "-" * 60,
        ]
        for entry in self.entries:
            checkin_str = (
                entry.last_checkin.strftime("%Y-%m-%d %H:%M:%S UTC")
                if entry.last_checkin
                else "never"
            )
            lines.append(
                f"[{entry.status_label():7s}] {entry.job_name}  "
                f"last={checkin_str}  next={entry.next_run.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
        return "\n".join(lines)


def build_digest(registry: JobRegistry) -> DigestReport:
    """Snapshot the current registry state into a DigestReport."""
    report = DigestReport()
    for job in registry.list_jobs():
        report.entries.append(
            DigestEntry(
                job_name=job.name,
                is_overdue=registry.is_overdue(job.name),
                last_checkin=registry.last_checkin(job.name),
                next_run=job.next_run(),
            )
        )
    report.entries.sort(key=lambda e: (not e.is_overdue, e.job_name))
    return report
