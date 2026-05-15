# Webhook Alert Backend

The `WebhookBackend` sends alert notifications to any HTTP endpoint that accepts
a JSON `POST` request — for example Slack incoming webhooks, PagerDuty Events
API, or a custom internal service.

## Configuration

Add a `webhook` section inside the `alert` block of your `croncheck.json`:

```json
{
  "alert": {
    "backend": "webhook",
    "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
    "webhook_timeout": 10,
    "webhook_extra_headers": {
      "X-Api-Key": "my-secret"
    },
    "webhook_extra_fields": {
      "environment": "production",
      "team": "platform"
    }
  }
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `webhook_url` | string | — | **Required.** Full URL to POST to. |
| `webhook_timeout` | int | `10` | Request timeout in seconds. |
| `webhook_extra_headers` | object | `{}` | Additional HTTP headers (e.g. auth tokens). |
| `webhook_extra_fields` | object | `{}` | Extra key/value pairs merged into every JSON body. |

## Payload format

Every request body is a JSON object with at least these two fields:

```json
{
  "job": "nightly-backup",
  "message": "Job nightly-backup is overdue by 300 s"
}
```

Any `webhook_extra_fields` are merged at the top level.

## Error handling

`WebhookBackend` never raises exceptions — HTTP errors and network failures are
logged at `ERROR` level so that a broken webhook endpoint does not crash the
daemon or suppress other alert backends.
