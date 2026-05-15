# Audit Log

Croncheck maintains an **audit log** that records every significant state transition for each monitored job. This gives operators a chronological history of check-ins, overdue events, alert dispatches, and recoveries.

## Events

| `event_type`        | When it is recorded |
|---------------------|---------------------|
| `checkin`           | A job successfully reported completion |
| `overdue`           | A job became overdue (missed its window) |
| `recovered`         | A previously-overdue job checked in again |
| `alert_sent`        | An alert was dispatched to a backend |
| `alert_suppressed`  | An alert was throttled / deduplicated |

## Storage format

Events are appended as **newline-delimited JSON** (JSONL) to a configurable file path. Each line is a self-contained JSON object:

```json
{"timestamp": "2024-05-01T12:00:00+00:00", "job_name": "db-backup", "event_type": "overdue", "detail": "job became overdue"}
```

## Configuration

Set `audit_log_path` in `appconfig` (or via the `CRONCHECK_AUDIT_LOG` environment variable) to enable file persistence. When unset, events are kept only in memory (useful for testing).

```json
{
  "audit_log_path": "/var/log/croncheck/audit.jsonl"
}
```

## Accessing recent events

The `AuditLog.recent()` method returns the most recent *n* events, optionally filtered by job name:

```python
from croncheck.audit import AuditLog

log = AuditLog(path="/var/log/croncheck/audit.jsonl")
log.load_from_file()

# Last 20 events for the db-backup job
for event in log.recent(n=20, job_name="db-backup"):
    print(event.timestamp, event.event_type, event.detail)
```

## Integration with Notifier

`AuditingNotifier` wraps the standard `Notifier` and automatically emits `overdue` and `recovered` events on every check cycle. Wrap it in `daemon.py` to activate auditing with zero changes to existing alert logic:

```python
from croncheck.audit import AuditLog
from croncheck.audit_middleware import AuditingNotifier

audit = AuditLog(path=config.audit_log_path)
audit.load_from_file()
auditing_notifier = AuditingNotifier(notifier, audit, registry)
```
