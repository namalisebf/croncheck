# Alert Retry Policy

`croncheck` can automatically retry alert delivery when a backend raises an
exception (e.g. transient network failure).

## Components

### `RetryPolicy`

Data-class that holds retry configuration:

| Field | Default | Description |
|---|---|---|
| `max_attempts` | `3` | Total delivery attempts (including the first). |
| `base_delay` | `1.0` | Seconds to wait before the second attempt. |
| `backoff_factor` | `2.0` | Multiplier applied to the delay on each retry. |
| `max_delay` | `30.0` | Upper bound on the inter-attempt sleep. |

**Delay schedule** (defaults): 0 s → 1 s → 2 s → 4 s …

### `RetryDispatcher`

Wraps any `AlertBackend` and adds retry logic:

```python
from croncheck.retry import RetryDispatcher, RetryPolicy
from croncheck.alerts import EmailBackend

policy = RetryPolicy(max_attempts=5, base_delay=2.0)
backend = EmailBackend(smtp_host="mail.example.com", to=["ops@example.com"])
dispatcher = RetryDispatcher(backend, policy)

# Used exactly like a regular backend:
dispatcher.send("nightly-backup", "Job is overdue by 10 minutes")
```

`send()` returns `True` on success and `False` when all attempts are exhausted.

## Integration with `Notifier`

Pass a `RetryDispatcher` in place of a plain backend when constructing
`Notifier`:

```python
from croncheck.notifier import Notifier
from croncheck.alerts import WebhookBackend
from croncheck.retry import RetryDispatcher, RetryPolicy

backend = RetryDispatcher(
    WebhookBackend(url="https://hooks.example.com/alert"),
    RetryPolicy(max_attempts=4),
)
notifier = Notifier(registry, backend)
```

## Logging

All retry activity is logged under the `croncheck.retry` logger at `DEBUG`
level; exhausted retries are logged at `ERROR`.
