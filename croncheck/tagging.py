"""Job tagging support: attach metadata tags to cron jobs and filter/query by them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional


@dataclass
class TagIndex:
    """Maintains a reverse index from tag -> set of job names."""

    _index: Dict[str, set] = field(default_factory=dict, repr=False)

    def add(self, job_name: str, tags: Iterable[str]) -> None:
        """Associate *tags* with *job_name*."""
        for tag in tags:
            self._index.setdefault(tag, set()).add(job_name)

    def remove(self, job_name: str) -> None:
        """Remove all tag associations for *job_name*."""
        for jobs in self._index.values():
            jobs.discard(job_name)
        # Clean up empty tag buckets.
        empty = [t for t, jobs in self._index.items() if not jobs]
        for t in empty:
            del self._index[t]

    def jobs_with_tag(self, tag: str) -> FrozenSet[str]:
        """Return job names that carry *tag*."""
        return frozenset(self._index.get(tag, set()))

    def jobs_with_all_tags(self, tags: Iterable[str]) -> FrozenSet[str]:
        """Return job names that carry ALL of the given *tags*."""
        tag_list = list(tags)
        if not tag_list:
            return frozenset()
        result: Optional[FrozenSet[str]] = None
        for tag in tag_list:
            bucket = self.jobs_with_tag(tag)
            result = bucket if result is None else result & bucket
        return result or frozenset()

    def all_tags(self) -> List[str]:
        """Return a sorted list of all known tags."""
        return sorted(self._index.keys())

    def tags_for_job(self, job_name: str) -> FrozenSet[str]:
        """Return all tags associated with *job_name*."""
        return frozenset(
            tag for tag, jobs in self._index.items() if job_name in jobs
        )
