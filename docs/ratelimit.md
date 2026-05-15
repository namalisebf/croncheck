# Alert Rate Limiting

Croncheck includes a sliding-window rate limiter that prevents alert storms
when a job is continuously overdue.

## How it works

The `RateLimiter` class tracks, per job name, how many alerts have been sent
within a configurable time window.  Once the limit is reached, further alerts
for that job are silently dropped until the window slides forward and old
timestamps expire.

```
window_seconds=3600, max_alerts=5
│◄──────── 1 hour ────────►│
  ✉ ✉ ✉ ✉ ✉  (5 sent → blocked until oldest expires)
```

## Usage

### Standalone

```python
from croncheck.ratelimit import RateLimiter

rl = RateLimiter(window_seconds=3600, max_alerts=5)

if rl.is_allowed("nightly-backup"):
    send_alert("nightly-backup")
    rl.record("nightly-backup")
```

### With the middleware wrapper

`RateLimitedNotifier` wraps any `Notifier` instance and transparently enforces
rate limits for both `check_and_notify` and `notify_failure` calls.

```python
from croncheck.notifier import Notifier
from croncheck.ratelimit import RateLimiter
from croncheck.ratelimit_middleware import RateLimitedNotifier

base_notifier = Notifier(registry, backend)
rl = RateLimiter(window_seconds=1800, max_alerts=3)
notifier = RateLimitedNotifier(base_notifier, rl)

# Use notifier.check_and_notify(registry) inside your daemon loop.
```

## Configuration reference

| Parameter        | Default | Description                                    |
|------------------|---------|------------------------------------------------|
| `window_seconds` | 3600    | Length of the sliding window in seconds        |
| `max_alerts`     | 5       | Maximum alerts allowed within the window       |

## Resetting a job

To clear the counter for a specific job (e.g. after a successful check-in):

```python
notifier.reset("nightly-backup")
```
