from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..events import _atomic_append_line, _canonical_event_json, load_events, make_event
from .model import ContextCategory, ContextItem, validate_context_key

CONTEXT_EVENTS_FILENAME = "context_events.jsonl"

CONTEXT_ITEM_SET = "CONTEXT_ITEM_SET"
CONTEXT_ITEM_ARCHIVED = "CONTEXT_ITEM_ARCHIVED"


def _context_item_to_payload(item: ContextItem) -> dict[str, Any]:
    return asdict(item)


def context_item_from_payload(payload: dict[str, Any]) -> ContextItem:
    return ContextItem(
        item_id=str(payload["item_id"]),
        category=payload["category"],
        key=str(payload["key"]),
        value=payload["value"],
        status=payload.get("status", "active"),
        jurisdiction=payload.get("jurisdiction"),
        confidence=payload.get("confidence"),
        source=payload.get("source"),
        notes=payload.get("notes"),
    )


def append_context_item_set_event(
    data_dir: Path,
    *,
    item: ContextItem,
    ts: int | None = None,
) -> Path:
    event = make_event(
        CONTEXT_ITEM_SET,
        _context_item_to_payload(item),
        ts=ts,
    )
    path = Path(data_dir) / CONTEXT_EVENTS_FILENAME
    _atomic_append_line(path, _canonical_event_json(event))
    return path


def append_context_item_archived_event(
    data_dir: Path,
    *,
    category: ContextCategory,
    key: str,
    ts: int | None = None,
) -> Path:
    validate_context_key(category, key)
    event = make_event(
        CONTEXT_ITEM_ARCHIVED,
        {
            "category": category,
            "key": key,
        },
        ts=ts,
    )
    path = Path(data_dir) / CONTEXT_EVENTS_FILENAME
    _atomic_append_line(path, _canonical_event_json(event))
    return path


def load_context_events(data_dir: Path):
    path = Path(data_dir) / CONTEXT_EVENTS_FILENAME
    if not path.is_file():
        return []
    return load_events(path)

