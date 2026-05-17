# Job Tagging

Croncheck supports attaching arbitrary string tags to cron jobs. Tags let you
organize, filter, and query jobs by team, environment, tier, or any custom
dimension.

## Quick Start

```python
from croncheck.registry import JobRegistry
from croncheck.tagging_middleware import TaggedRegistry
from croncheck.schedule import CronJob

registry = JobRegistry()
tagged = TaggedRegistry(registry)

job = CronJob(name="nightly-backup", cron="0 2 * * *", grace_seconds=300)
tagged.register(job, tags=["env:prod", "team:ops", "tier:critical"])
```

## Querying by Tag

### Jobs with a single tag

```python
ops_jobs = tagged.jobs_with_tag("team:ops")
```

### Jobs matching ALL tags (intersection)

```python
critical_prod = tagged.jobs_with_all_tags(["env:prod", "tier:critical"])
```

### Tags on a specific job

```python
tags = tagged.tags_for_job("nightly-backup")
# frozenset({'env:prod', 'team:ops', 'tier:critical'})
```

### All known tags

```python
all_tags = tagged.all_tags()  # sorted list
```

## Unregistering

When a job is unregistered its tag associations are automatically removed:

```python
tagged.unregister("nightly-backup")
```

## TagIndex (low-level)

`TagIndex` is the underlying reverse-index data structure and can be used
independently of `TaggedRegistry` if needed:

```python
from croncheck.tagging import TagIndex

idx = TagIndex()
idx.add("job_a", ["x", "y"])
idx.jobs_with_tag("x")          # frozenset({'job_a'})
idx.jobs_with_all_tags(["x", "y"])  # frozenset({'job_a'})
idx.remove("job_a")
```

## Tag Conventions

We recommend namespaced tags using a `key:value` format:

| Tag | Meaning |
|-----|---------|
| `env:prod` | Production environment |
| `env:staging` | Staging environment |
| `team:ops` | Owned by operations team |
| `tier:critical` | Critical business job |
| `notify:pagerduty` | Route alerts to PagerDuty |
