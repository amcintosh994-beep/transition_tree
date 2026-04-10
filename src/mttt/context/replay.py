from __future__ import annotations

from pathlib import Path

from .events import (
    CONTEXT_ITEM_ARCHIVED,
    CONTEXT_ITEM_SET,
    context_item_from_payload,
    load_context_events,
)
from .model import ContextItem, ReplayedContext


def replay_context(data_dir: Path) -> ReplayedContext:
    events = load_context_events(data_dir)

    current_state: dict[str, ContextItem] = {}
    constraints: dict[str, ContextItem] = {}
    priorities: dict[str, ContextItem] = {}

    buckets = {
        "current_state": current_state,
        "constraint": constraints,
        "priority": priorities,
    }

    for ev in events:
        if ev.type == CONTEXT_ITEM_SET:
            item = context_item_from_payload(ev.payload)
            buckets[item.category][item.key] = item
            continue

        if ev.type == CONTEXT_ITEM_ARCHIVED:
            category = ev.payload["category"]
            key = ev.payload["key"]
            buckets[category].pop(key, None)
            continue

        raise ValueError(f"Unknown context event type: {ev.type!r}")

    return ReplayedContext(
        current_state=current_state,
        constraints=constraints,
        priorities=priorities,
    )

