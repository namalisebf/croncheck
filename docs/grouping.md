# Job Grouping

Croncheck supports organising jobs into named **groups**, making it easy to
query or report on related jobs together (e.g. all `nightly` jobs, all
`team-payments` jobs).

## Core classes

### `GroupIndex` (`croncheck/grouping.py`)

A pure data structure that maintains a bidirectional mapping between job names
and group names.

```python
from croncheck.grouping import GroupIndex

idx = GroupIndex()
idx.add("backup-db", "nightly")
idx.add("backup-files", "nightly")

print(idx.jobs_in_group("nightly"))  # {'backup-db', 'backup-files'}
print(idx.group_of("backup-db"))    # 'nightly'
```

Key behaviours:

- A job can belong to **at most one** group at a time.  Re-assigning a job
  moves it from the old group to the new one automatically.
- Removing the last job from a group also removes the group entry, keeping
  the index clean.

### `GroupedRegistry` (`croncheck/grouping_middleware.py`)

A middleware wrapper around `JobRegistry` that transparently maintains a
`GroupIndex` alongside the normal registry operations.

```python
from croncheck.grouping_middleware import GroupedRegistry
from croncheck.schedule import CronJob

reg = GroupedRegistry()
reg.register(CronJob("backup-db", "0 2 * * *", grace_seconds=300), group="nightly")
reg.register(CronJob("send-report", "0 8 * * 1", grace_seconds=600), group="weekly")

# Query
print(reg.jobs_in_group("nightly"))  # {'backup-db'}
print(reg.group_of("send-report"))   # 'weekly'
print(list(reg.all_groups()))        # ['nightly', 'weekly']

# Reassign after the fact
reg.assign_group("backup-db", "critical")
```

All standard `JobRegistry` operations (`checkin`, `unregister`, `overdue_jobs`)
are forwarded unchanged.

## Integration with alerting

You can filter `overdue_jobs()` by group to send targeted alerts:

```python
nightly_jobs = {
    name: reg.jobs[name]
    for name in reg.jobs_in_group("nightly")
}
overdue_nightly = [j for j in nightly_jobs.values() if j.is_overdue()]
```
