"""Job grouping support: organise jobs into named groups and query by group."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, Set


@dataclass
class GroupIndex:
    """Maps group names to sets of job names."""

    _groups: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _job_group: Dict[str, str] = field(default_factory=dict)

    def add(self, job_name: str, group: str) -> None:
        """Assign *job_name* to *group*, replacing any previous assignment."""
        old = self._job_group.get(job_name)
        if old is not None and old != group:
            self._groups[old].discard(job_name)
            if not self._groups[old]:
                del self._groups[old]
        self._groups[group].add(job_name)
        self._job_group[job_name] = group

    def remove(self, job_name: str) -> None:
        """Remove *job_name* from its group entirely."""
        group = self._job_group.pop(job_name, None)
        if group is not None:
            self._groups[group].discard(job_name)
            if not self._groups[group]:
                del self._groups[group]

    def group_of(self, job_name: str) -> str | None:
        """Return the group name for *job_name*, or ``None`` if ungrouped."""
        return self._job_group.get(job_name)

    def jobs_in_group(self, group: str) -> Set[str]:
        """Return the set of job names assigned to *group*."""
        return set(self._groups.get(group, set()))

    def all_groups(self) -> Iterable[str]:
        """Return all known group names."""
        return list(self._groups.keys())
