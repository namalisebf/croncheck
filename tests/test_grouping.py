"""Tests for croncheck.grouping and croncheck.grouping_middleware."""
from __future__ import annotations

import pytest

from croncheck.grouping import GroupIndex
from croncheck.grouping_middleware import GroupedRegistry
from croncheck.schedule import CronJob


# ---------------------------------------------------------------------------
# GroupIndex unit tests
# ---------------------------------------------------------------------------

class TestGroupIndex:
    def _index(self) -> GroupIndex:
        return GroupIndex()

    def test_add_and_jobs_in_group(self):
        idx = self._index()
        idx.add("backup", "nightly")
        assert "backup" in idx.jobs_in_group("nightly")

    def test_unknown_group_returns_empty(self):
        idx = self._index()
        assert idx.jobs_in_group("ghost") == set()

    def test_group_of_returns_group(self):
        idx = self._index()
        idx.add("sync", "hourly")
        assert idx.group_of("sync") == "hourly"

    def test_group_of_unknown_returns_none(self):
        idx = self._index()
        assert idx.group_of("missing") is None

    def test_reassign_moves_job(self):
        idx = self._index()
        idx.add("job", "a")
        idx.add("job", "b")
        assert "job" not in idx.jobs_in_group("a")
        assert "job" in idx.jobs_in_group("b")
        assert "a" not in idx.all_groups()

    def test_remove_clears_job(self):
        idx = self._index()
        idx.add("job", "g")
        idx.remove("job")
        assert idx.group_of("job") is None
        assert idx.jobs_in_group("g") == set()

    def test_remove_cleans_empty_group(self):
        idx = self._index()
        idx.add("only", "solo")
        idx.remove("only")
        assert "solo" not in list(idx.all_groups())

    def test_all_groups_lists_groups(self):
        idx = self._index()
        idx.add("a", "g1")
        idx.add("b", "g2")
        groups = list(idx.all_groups())
        assert set(groups) == {"g1", "g2"}


# ---------------------------------------------------------------------------
# GroupedRegistry integration tests
# ---------------------------------------------------------------------------

def _make_job(name: str) -> CronJob:
    return CronJob(name=name, expression="* * * * *", grace_seconds=60)


class TestGroupedRegistry:
    def test_register_with_group(self):
        reg = GroupedRegistry()
        reg.register(_make_job("j1"), group="team-a")
        assert "j1" in reg.jobs_in_group("team-a")

    def test_register_without_group(self):
        reg = GroupedRegistry()
        reg.register(_make_job("j2"))
        assert reg.group_of("j2") is None

    def test_assign_group_after_register(self):
        reg = GroupedRegistry()
        reg.register(_make_job("j3"))
        reg.assign_group("j3", "team-b")
        assert reg.group_of("j3") == "team-b"

    def test_assign_group_unknown_job_raises(self):
        reg = GroupedRegistry()
        with pytest.raises(KeyError):
            reg.assign_group("ghost", "team-x")

    def test_unregister_removes_from_group(self):
        reg = GroupedRegistry()
        reg.register(_make_job("j4"), group="g")
        reg.unregister("j4")
        assert reg.jobs_in_group("g") == set()

    def test_jobs_in_group_multiple(self):
        reg = GroupedRegistry()
        reg.register(_make_job("x"), group="ops")
        reg.register(_make_job("y"), group="ops")
        assert reg.jobs_in_group("ops") == {"x", "y"}
