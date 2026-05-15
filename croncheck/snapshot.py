"""Snapshot helpers — extract serialisable state from a JobRegistry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from croncheck.registry import JobRegistry


def registry_to_state(registry: "JobRegistry") -> Dict[str, dict]:
    """Convert a JobRegistry's runtime state into a plain dict suitable
    for persistence via StateStore.
    """
    snapshot: Dict[str, dict] = {}
    for name, job in registry.jobs.items():
        snapshot[name] = {
            "last_checkin": registry.last_checkin.get(name),
            "alerted": registry.alerted.get(name, False),
        }
    return snapshot


def apply_state_to_registry(state: Dict[str, dict], registry: "JobRegistry") -> None:
    """Restore persisted state into a live JobRegistry instance.
    Only updates entries for jobs that are currently registered.
    """
    for name, entry in state.items():
        if name not in registry.jobs:
            continue
        last_checkin = entry.get("last_checkin")
        if last_checkin is not None:
            registry.last_checkin[name] = last_checkin
        registry.alerted[name] = entry.get("alerted", False)
