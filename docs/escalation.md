# Alert Escalation

Croncheck supports automatic alert **escalation**: as a job accumulates consecutive
missed check-ins the alert level rises from `normal` → `warning` → `critical`.
This lets you route critical alerts to on-call channels while keeping routine
warnings in a lower-priority queue.

## How It Works

1. `EscalationPolicy` tracks a **consecutive miss counter** per job.
2. Each call to `record_miss(job_name)` increments the counter and returns the
   current level string (`"normal"`, `"warning"`, or `"critical"`).
3. A successful check-in via `record_checkin(job_name)` resets the counter
   (unless `reset_on_checkin=False`).

### Thresholds (defaults)

| Level      | After N consecutive misses |
|------------|----------------------------|
| `normal`   | < 2                        |
| `warning`  | ≥ 2                        |
| `critical` | ≥ 5                        |

## Configuration

```python
from croncheck.escalation import EscalationPolicy

policy = EscalationPolicy(
    warning_after=3,   # escalate to WARNING after 3 misses
    critical_after=8,  # escalate to CRITICAL after 8 misses
    reset_on_checkin=True,
)
```

## Integration with the Notifier

Wrap your existing `Notifier` with `EscalatingNotifier`:

```python
from croncheck.escalation_notifier import EscalatingNotifier
from croncheck.escalation import EscalationPolicy

notifier = EscalatingNotifier(
    inner=base_notifier,
    registry=registry,
    policy=EscalationPolicy(warning_after=2, critical_after=5),
)

# In your daemon loop:
notifier.check_and_notify()
```

The `escalation_level` key is injected into the `extra` dict passed to
`notify_failure`, so alert backends can include it in the message body or
use it to select a delivery channel.

## Checking the Current Level

```python
level = notifier.current_level("nightly-backup")
print(level)  # "warning"
```

This is also surfaced by the health-check HTTP endpoint when the escalating
notifier is wired into the daemon.
