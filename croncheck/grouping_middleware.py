"""Middleware that wraps a JobRegistry and maintains a GroupIndex."""
from __future__ import annotations

from typing import Optional, Set

from croncheck.grouping import GroupIndex
from croncheck.registry import JobRegistry
from croncheck.schedule import CronJob


class GroupedRegistry:
    """A thin wrapper around :class:`JobRegistry` that also tracks job groups.

    Jobs can be registered with an optional *group* keyword argument.  All
    other operations are delegated to the underlying registry unchanged.
    """

    def __init__(self, registry: Optional[JobRegistry] = None) -> None:
        self._registry = registry or JobRegistry()
        self._index = GroupIndex()

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    @property
    def jobs(self):
        return self._registry.jobs

    def register(self, job: CronJob, *, group: Optional[str] = None) -> None:
        """Register *job*, optionally placing it in *group*."""
        self._registry.register(job)
        if group is not None:
            self._index.add(job.name, group)

    def unregister(self, job_name: str) -> None:
        self._index.remove(job_name)
        self._registry.unregister(job_name)

    def checkin(self, job_name: str, **kwargs) -> None:
        self._registry.checkin(job_name, **kwargs)

    def assign_group(self, job_name: str, group: str) -> None:
        """Assign an already-registered job to a group (or change its group)."""
        if job_name not in self._registry.jobs:
            raise KeyError(f"Unknown job: {job_name!r}")
        self._index.add(job_name, group)

    def jobs_in_group(self, group: str) -> Set[str]:
        """Return the set of job names belonging to *group*."""
        return self._index.jobs_in_group(group)

    def group_of(self, job_name: str) -> Optional[str]:
        """Return the group name for *job_name*, or ``None`` if ungrouped."""
        return self._index.group_of(job_name)

    def all_groups(self):
        return self._index.all_groups()

    def overdue_jobs(self):
        return self._registry.overdue_jobs()
