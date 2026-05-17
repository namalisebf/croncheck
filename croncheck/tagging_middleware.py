"""Middleware that integrates TagIndex with JobRegistry for tag-aware filtering."""
from __future__ import annotations

from typing import Iterable, List

from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob
from croncheck.tagging import TagIndex


class TaggedRegistry:
    """Wraps a JobRegistry and keeps a TagIndex in sync."""

    def __init__(self, registry: JobRegistry) -> None:
        self._registry = registry
        self._tags = TagIndex()

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    def register(self, job: CronJob, tags: Iterable[str] = ()) -> None:
        """Register *job* and associate it with *tags*."""
        self._registry.register(job)
        self._tags.add(job.name, tags)

    def unregister(self, job_name: str) -> None:
        """Unregister job and remove its tag associations."""
        self._registry.unregister(job_name)
        self._tags.remove(job_name)

    def checkin(self, job_name: str) -> None:
        self._registry.checkin(job_name)

    # ------------------------------------------------------------------
    # Tag-aware queries
    # ------------------------------------------------------------------

    def jobs_with_tag(self, tag: str) -> List[CronJob]:
        """Return CronJob objects that carry *tag*."""
        names = self._tags.jobs_with_tag(tag)
        return [j for j in self._registry.all_jobs() if j.name in names]

    def jobs_with_all_tags(self, tags: Iterable[str]) -> List[CronJob]:
        """Return CronJob objects that carry ALL of *tags*."""
        names = self._tags.jobs_with_all_tags(tags)
        return [j for j in self._registry.all_jobs() if j.name in names]

    def tags_for_job(self, job_name: str):
        return self._tags.tags_for_job(job_name)

    def all_tags(self):
        return self._tags.all_tags()

    # Expose underlying registry for compatibility.
    @property
    def registry(self) -> JobRegistry:
        return self._registry
