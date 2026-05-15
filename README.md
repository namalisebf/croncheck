# croncheck

Lightweight daemon that monitors cron job execution and sends alerts on missed or failed runs.

## Installation

```bash
pip install croncheck
```

## Usage

Register a cron job for monitoring by wrapping your command with `croncheck`:

```bash
croncheck run --id "backup-job" --schedule "0 2 * * *" -- /usr/local/bin/backup.sh
```

Or configure jobs via a YAML config file:

```yaml
# croncheck.yml
jobs:
  - id: backup-job
    schedule: "0 2 * * *"
    command: /usr/local/bin/backup.sh
    alert:
      email: ops@example.com
      grace_period: 10m
```

Then start the daemon:

```bash
croncheck start --config croncheck.yml
```

Check the status of monitored jobs:

```bash
croncheck status
```

### Alert Channels

croncheck supports alerting via **email**, **Slack**, and **PagerDuty**. Configure your preferred channel in `croncheck.yml` under the `alert` key.

## Requirements

- Python 3.8+
- A running cron daemon (or any scheduler)

## License

This project is licensed under the [MIT License](LICENSE).