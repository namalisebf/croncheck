"""Tests for croncheck.tagging and croncheck.tagging_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from croncheck.tagging import TagIndex
from croncheck.tagging_middleware import TaggedRegistry


# ---------------------------------------------------------------------------
# TagIndex unit tests
# ---------------------------------------------------------------------------

class TestTagIndex:
    def test_add_and_jobs_with_tag(self):
        idx = TagIndex()
        idx.add("job_a", ["team:ops", "env:prod"])
        assert "job_a" in idx.jobs_with_tag("team:ops")
        assert "job_a" in idx.jobs_with_tag("env:prod")

    def test_unknown_tag_returns_empty(self):
        idx = TagIndex()
        assert idx.jobs_with_tag("nonexistent") == frozenset()

    def test_remove_clears_job(self):
        idx = TagIndex()
        idx.add("job_a", ["env:prod"])
        idx.remove("job_a")
        assert idx.jobs_with_tag("env:prod") == frozenset()

    def test_remove_cleans_empty_tag_buckets(self):
        idx = TagIndex()
        idx.add("job_a", ["solo"])
        idx.remove("job_a")
        assert "solo" not in idx.all_tags()

    def test_jobs_with_all_tags_intersection(self):
        idx = TagIndex()
        idx.add("job_a", ["x", "y"])
        idx.add("job_b", ["x"])
        result = idx.jobs_with_all_tags(["x", "y"])
        assert result == frozenset({"job_a"})

    def test_jobs_with_all_tags_empty_input(self):
        idx = TagIndex()
        idx.add("job_a", ["x"])
        assert idx.jobs_with_all_tags([]) == frozenset()

    def test_tags_for_job(self):
        idx = TagIndex()
        idx.add("job_a", ["a", "b"])
        assert idx.tags_for_job("job_a") == frozenset({"a", "b"})

    def test_all_tags_sorted(self):
        idx = TagIndex()
        idx.add("job_a", ["z", "a", "m"])
        assert idx.all_tags() == ["a", "m", "z"]


# ---------------------------------------------------------------------------
# TaggedRegistry integration tests
# ---------------------------------------------------------------------------

def _make_job(name="backup"):
    job = MagicMock()
    job.name = name
    return job


def _make_tagged_registry():
    mock_reg = MagicMock()
    mock_reg.all_jobs.return_value = []
    return TaggedRegistry(mock_reg)


class TestTaggedRegistry:
    def test_register_delegates_to_inner_registry(self):
        tr = _make_tagged_registry()
        job = _make_job("nightly")
        tr.register(job, ["env:prod"])
        tr.registry.register.assert_called_once_with(job)

    def test_unregister_removes_tags(self):
        tr = _make_tagged_registry()
        job = _make_job("nightly")
        tr.register(job, ["env:prod"])
        tr.unregister("nightly")
        assert tr.tags_for_job("nightly") == frozenset()

    def test_jobs_with_tag_filters_correctly(self):
        job_a = _make_job("job_a")
        job_b = _make_job("job_b")
        mock_reg = MagicMock()
        mock_reg.all_jobs.return_value = [job_a, job_b]
        tr = TaggedRegistry(mock_reg)
        tr.register(job_a, ["team:ops"])
        tr.register(job_b, ["team:dev"])
        result = tr.jobs_with_tag("team:ops")
        assert result == [job_a]

    def test_jobs_with_all_tags(self):
        job_a = _make_job("job_a")
        mock_reg = MagicMock()
        mock_reg.all_jobs.return_value = [job_a]
        tr = TaggedRegistry(mock_reg)
        tr.register(job_a, ["x", "y"])
        assert tr.jobs_with_all_tags(["x", "y"]) == [job_a]
        assert tr.jobs_with_all_tags(["x", "z"]) == []

    def test_checkin_delegates(self):
        tr = _make_tagged_registry()
        tr.checkin("some_job")
        tr.registry.checkin.assert_called_once_with("some_job")
