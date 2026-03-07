from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Iterable, List, Type, TypeVar

from .model import Edge, Node


EVENTS_FILENAME = "events.jsonl"
EVENT_SCHEMA_VERSION = 1

T = TypeVar("T")


@dataclass(frozen=True)
class Event:
    v: int
    ts: int
    type: str
    payload: Any


@dataclass(frozen=True)
class MaterializedState:
    nodes: List[Node]
    edges: List[Edge]


def _parse_event_line(line: str, line_no: int) -> Event:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in events.jsonl at line {line_no}: {e}") from e

    if not isinstance(obj, dict):
        raise ValueError(f"Event at line {line_no} must be a JSON object")

    for key in ("v", "ts", "type", "payload"):
        if key not in obj:
            raise ValueError(f"Event at line {line_no} missing required key: {key!r}")

    v = obj["v"]
    ts = obj["ts"]
    typ = obj["type"]
    payload = obj["payload"]

    if not isinstance(v, int):
        raise ValueError(f"Event at line {line_no} has non-int 'v'")
    if not isinstance(ts, int):
        raise ValueError(f"Event at line {line_no} has non-int 'ts'")
    if not isinstance(typ, str):
        raise ValueError(f"Event at line {line_no} has non-str 'type'")

    return Event(v=v, ts=ts, type=typ, payload=payload)


def load_events(events_path: Path) -> List[Event]:
    if not events_path.is_file():
        raise FileNotFoundError(f"Missing events log: {events_path}")

    lines = events_path.read_text(encoding="utf-8").splitlines()
    events: List[Event] = []

    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        events.append(_parse_event_line(line, i))

    return events


def _from_dict(cls: Type[T], obj: Any) -> T:
    if not isinstance(obj, dict):
        raise ValueError(f"Expected object for {cls.__name__}, got {type(obj).__name__}")

    allowed = {f.name for f in fields(cls)}
    extra = set(obj.keys()) - allowed
    if extra:
        raise ValueError(f"Unexpected keys for {cls.__name__}: {sorted(extra)}")

    return cls(**obj)


def _materialize_set_state_payload(payload: Any) -> MaterializedState:
    if not isinstance(payload, dict):
        raise ValueError("SET_STATE payload must be an object")

    if "nodes" not in payload or "edges" not in payload:
        raise ValueError("SET_STATE payload must contain 'nodes' and 'edges'")

    raw_nodes = payload["nodes"]
    raw_edges = payload["edges"]

    if not isinstance(raw_nodes, list):
        raise ValueError("SET_STATE payload 'nodes' must be a list")
    if not isinstance(raw_edges, list):
        raise ValueError("SET_STATE payload 'edges' must be a list")

    nodes = [_from_dict(Node, x) for x in raw_nodes]
    edges = [_from_dict(Edge, x) for x in raw_edges]

    return MaterializedState(nodes=nodes, edges=edges)


def replay_events(events: Iterable[Event]) -> MaterializedState:
    state: MaterializedState | None = None

    for ev in events:
        if ev.v != EVENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported event schema version: {ev.v} "
                f"(expected {EVENT_SCHEMA_VERSION})"
            )

        if ev.type == "SET_STATE":
            state = _materialize_set_state_payload(ev.payload)
            continue

        raise ValueError(f"Unknown event type: {ev.type!r}")

    if state is None:
        raise ValueError("Replay produced no state; events log contained no SET_STATE event")

    return state


def load_and_replay_events(data_dir: Path) -> MaterializedState:
    events_path = data_dir / EVENTS_FILENAME
    events = load_events(events_path)
    return replay_events(events)


def node_to_dict(node: Node) -> dict[str, Any]:
    return asdict(node)


def edge_to_dict(edge: Edge) -> dict[str, Any]:
    return asdict(edge)
