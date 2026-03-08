from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Iterable, List, Type, TypeVar

from .loader_json import load_nodes_edges_from_dir
from .model import Edge, Node
from .normalize_json import _edge_to_obj, _node_to_obj, save_nodes_edges_to_dir


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


def export_event_fixture(
    source_dir: Path,
    out_dir: Path,
    *,
    ts: int | None = None,
    include_materialized_snapshot: bool = True,
) -> Path:
    """
    Create a clean event fixture directory from canonical snapshot state.

    Behavior:
    - load canonical nodes/edges from source_dir
    - create out_dir if needed
    - write a single canonical SET_STATE event to out_dir/events.jsonl
    - optionally materialize canonical nodes.json / edges.json into out_dir

    Returns the output directory path.
    """
    source_dir = Path(source_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    nodes, edges = load_nodes_edges_from_dir(source_dir)

    # overwrite events.jsonl with one canonical SET_STATE event
    payload = {
        "nodes": [node_to_dict(n) for n in nodes],
        "edges": [edge_to_dict(e) for e in edges],
    }
    event = make_event("SET_STATE", payload, ts=ts)
    line = _canonical_event_json(event)
    _atomic_write_text(out_dir / EVENTS_FILENAME, line)

    if include_materialized_snapshot:
        save_nodes_edges_to_dir(out_dir, nodes, edges)

    return out_dir



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

    with tempfile.TemporaryDirectory(prefix="mttt_replay_") as td:
        tmp_dir = Path(td)

        (tmp_dir / "nodes.json").write_text(
            json.dumps(raw_nodes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (tmp_dir / "edges.json").write_text(
            json.dumps(raw_edges, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        nodes, edges = load_nodes_edges_from_dir(tmp_dir)

    return MaterializedState(nodes=nodes, edges=edges)

def _atomic_write_text(path: Path, text: str) -> None:
    """
    Atomically write UTF-8 text with LF endings and a trailing newline.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"

    tmp_dir = str(path.parent)
    prefix = f".{path.name}.tmp."
    fd, tmp_name = tempfile.mkstemp(prefix=prefix, dir=tmp_dir, text=True)
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass




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
    return _node_to_obj(node)


def edge_to_dict(edge: Edge) -> dict[str, Any]:
    return _edge_to_obj(edge)
    
def _canonical_event_json(event: dict[str, Any]) -> str:
    return json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _atomic_append_line(path: Path, line: str) -> None:
    """
    Deterministically append one LF-terminated line to a text file.

    Properties:
    - UTF-8 (no BOM)
    - LF-only
    - append-only semantics
    - no blank line insertion
    - file created if missing
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if "\r" in line or "\n" in line:
        raise ValueError("append line must be a single logical line without embedded newlines")

    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        existing = existing.replace("\r\n", "\n").replace("\r", "\n")

    new_text = existing + line + "\n"

    tmp_dir = str(path.parent)
    prefix = f".{path.name}.tmp."
    fd, tmp_name = tempfile.mkstemp(prefix=prefix, dir=tmp_dir, text=True)
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass

def make_event(event_type: str, payload: Any, *, ts: int | None = None) -> dict[str, Any]:
    if not isinstance(event_type, str) or not event_type:
        raise ValueError("event_type must be a non-empty string")

    if ts is None:
        ts = int(time.time())

    return {
        "v": EVENT_SCHEMA_VERSION,
        "ts": ts,
        "type": event_type,
        "payload": payload,
    }

def append_event(data_dir: Path, event: dict[str, Any]) -> Path:
    """
    Append one canonical event to events.jsonl.

    Returns the path written.
    """
    if not isinstance(event, dict):
        raise ValueError("event must be a dict")

    for key in ("v", "ts", "type", "payload"):
        if key not in event:
            raise ValueError(f"event missing required key: {key!r}")

    path = Path(data_dir) / EVENTS_FILENAME
    line = _canonical_event_json(event)
    _atomic_append_line(path, line)
    return path

def append_set_state_event(data_dir: Path, nodes: List[Node], edges: List[Edge], *, ts: int | None = None) -> Path:
    payload = {
        "nodes": [node_to_dict(n) for n in nodes],
        "edges": [edge_to_dict(e) for e in edges],
    }
    event = make_event("SET_STATE", payload, ts=ts)
    return append_event(data_dir, event)
    
def replay_summary(data_dir: Path) -> dict[str, int | str]:
    """
    Return a small summary of the event log and replayed end state.
    """
    data_dir = Path(data_dir)
    events_path = data_dir / EVENTS_FILENAME

    events = load_events(events_path)
    materialized = replay_events(events)

    last_event_ts = events[-1].ts if events else None

    return {
        "events_jsonl": "present" if events_path.is_file() else "missing",
        "events": len(events),
        "last_event_ts": last_event_ts if last_event_ts is not None else "none",
        "state_nodes": len(materialized.nodes),
        "state_edges": len(materialized.edges),
        "regime": "events",
    }


def compact_events_in_dir(data_dir: Path, *, ts: int | None = None) -> Path:
    """
    Replay events.jsonl and rewrite it as a single canonical SET_STATE event.

    Returns the path written.
    """
    data_dir = Path(data_dir)
    materialized = load_and_replay_events(data_dir)

    payload = {
        "nodes": [node_to_dict(n) for n in materialized.nodes],
        "edges": [edge_to_dict(e) for e in materialized.edges],
    }
    event = make_event("SET_STATE", payload, ts=ts)
    line = _canonical_event_json(event)

    path = data_dir / EVENTS_FILENAME
    _atomic_write_text(path, line)
    return path



def materialize_events_to_dir(data_dir: Path) -> MaterializedState:
    """
    Replay events.jsonl and write canonical nodes.json / edges.json
    into the same directory.

    Returns the materialized typed state.
    """
    data_dir = Path(data_dir)
    materialized = load_and_replay_events(data_dir)
    save_nodes_edges_to_dir(data_dir, materialized.nodes, materialized.edges)
    return materialized

