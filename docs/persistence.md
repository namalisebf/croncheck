# Persistence

`croncheck` can survive daemon restarts without losing track of which jobs
have already been alerted or when they last checked in.

## How it works

1. **`StateStore`** (`croncheck/persistence.py`) writes a JSON file to disk
   using an atomic `rename` so a crash during a write never corrupts the
   existing state.
2. **`registry_to_state`** / **`apply_state_to_registry`**
   (`croncheck/snapshot.py`) convert between the live `JobRegistry` and the
   plain dict that `StateStore` expects.
3. The daemon calls `StateStore.save()` on a configurable interval (and on
   clean shutdown) and calls `StateStore.load()` + `apply_state_to_registry()`
   on startup.

## State file format

```json
{
  "backup-job": {
    "last_checkin": "2024-05-01T12:00:00.000000+00:00",
    "alerted": false
  },
  "report-job": {
    "last_checkin": null,
    "alerted": true
  }
}
```

| Field          | Type              | Description                                      |
|----------------|-------------------|--------------------------------------------------|
| `last_checkin` | ISO-8601 UTC or `null` | Timestamp of the most recent successful check-in |
| `alerted`      | bool              | Whether an overdue alert has already been sent   |

## Configuration

Pass `state_path` when constructing `CronCheckDaemon`:

```python
from croncheck.daemon import CronCheckDaemon
from croncheck.persistence import StateStore

daemon = CronCheckDaemon(
    registry=registry,
    notifier=notifier,
    state_store=StateStore("/var/lib/croncheck/state.json"),
    state_save_interval=60,   # seconds
)
```

If `state_store` is omitted, state is kept in memory only.
