"""Command-line interface for croncheck."""

import argparse
import json
import sys
from datetime import datetime, timezone

from croncheck.registry import JobRegistry
from croncheck.persistence import StateStore
from croncheck.snapshot import apply_state_to_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="croncheck",
        description="Monitor cron job execution and alert on missed or failed runs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # croncheck status
    status_p = sub.add_parser("status", help="Show status of all registered jobs.")
    status_p.add_argument(
        "--state-file",
        default="croncheck_state.json",
        help="Path to the persisted state file (default: croncheck_state.json).",
    )
    status_p.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output status as JSON.",
    )

    # croncheck checkin
    checkin_p = sub.add_parser("checkin", help="Record a successful job check-in.")
    checkin_p.add_argument("job_name", help="Name of the job to check in.")
    checkin_p.add_argument(
        "--state-file",
        default="croncheck_state.json",
        help="Path to the persisted state file.",
    )

    return parser


def cmd_status(args: argparse.Namespace) -> int:
    store = StateStore(args.state_file)
    state = store.load()

    if not state:
        print("No jobs found in state file.", file=sys.stderr)
        return 1

    registry = JobRegistry()
    apply_state_to_registry(registry, state)

    now = datetime.now(timezone.utc)
    rows = []
    for name, job in registry.jobs.items():
        overdue = job.is_overdue(now)
        last = job.last_checkin.isoformat() if job.last_checkin else "never"
        rows.append({"name": name, "overdue": overdue, "last_checkin": last})

    if args.output_json:
        print(json.dumps(rows, indent=2))
    else:
        fmt = "{:<30} {:<10} {}"
        print(fmt.format("JOB", "OVERDUE", "LAST CHECK-IN"))
        print("-" * 60)
        for r in rows:
            print(fmt.format(r["name"], str(r["overdue"]), r["last_checkin"]))
    return 0


def cmd_checkin(args: argparse.Namespace) -> int:
    store = StateStore(args.state_file)
    state = store.load()

    registry = JobRegistry()
    if state:
        apply_state_to_registry(registry, state)

    if args.job_name not in registry.jobs:
        print(f"Job '{args.job_name}' not found in state file.", file=sys.stderr)
        return 1

    registry.checkin(args.job_name)
    from croncheck.snapshot import registry_to_state
    store.save(registry_to_state(registry))
    print(f"Check-in recorded for '{args.job_name}'.")
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "checkin":
        return cmd_checkin(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
