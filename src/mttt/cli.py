from __future__ import annotations
from collections import deque

import argparse
from pathlib import Path
import json
import sys

from .normalize_json import normalize_dir
from .pipeline import compute_ui_state

EVENTS_FILENAME = "events.jsonl"

def _print_json(obj: dict) -> None:
    import json
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2))


def cmd_events_head(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    events_path = data_dir / "events.jsonl"

    if not events_path.is_file():
        result = {
            "events_jsonl": "missing",
            "events": 0,
            "first_event_ts": None,
            "last_event_ts": None,
        }
        if args.json:
            _print_json(result)
        else:
            print("events.jsonl: missing")
        return 1

    count = 0
    first_ts = None
    last_ts = None

    with events_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            ev = json.loads(line)
            ts = ev.get("ts")

            if ts is None:
                continue

            if first_ts is None:
                first_ts = ts

            last_ts = ts
            count += 1

    result = {
        "events_jsonl": "present",
        "events": count,
        "first_event_ts": first_ts,
        "last_event_ts": last_ts,
    }

    if args.json:
        _print_json(result)
    else:
        print("events.jsonl: present")
        print(f"events: {count}")
        print(f"first_event_ts: {first_ts if first_ts is not None else 'none'}")
        print(f"last_event_ts: {last_ts if last_ts is not None else 'none'}")

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    from .state_provider import load_state
    from .knowledge.registry import load_knowledge_registry

    loaded = load_state(
        Path(args.data_dir),
        regime=args.state_regime,
        until_ts=args.until_ts,
    )

    knowledge_registry = None
    if args.with_knowledge:
        knowledge_registry = load_knowledge_registry(Path(args.data_dir))

    ui = compute_ui_state(
        loaded.nodes,
        loaded.edges,
        preferred_domain=args.preferred_domain,
        knowledge_registry=knowledge_registry,
    )

    inv = ui.get("invariants")
    if inv is not None and not getattr(inv, "ok", True):
        print("INVARIANTS FAILED")
        for e in getattr(inv, "errors", []):
            print(f"- {e}")

        proposals = ui.get("scaffold_proposals") or {}
        if proposals:
            print("Scaffold proposals:")
            for goal_id in sorted(proposals.keys()):
                items = proposals[goal_id]
                print(f"- {goal_id}: {len(items)} proposal(s)")
                for p in items:
                    print(
                        f"  - {p.scaffold_id}: "
                        f"{len(p.proposed_nodes)} node(s), "
                        f"{len(p.proposed_edges)} edge(s)"
                    )
        return 2

    issues = ui.get("cnl_issues") or []
    if issues:
        print("CNL LINT FAILED")
        for i in issues:
            node_id = getattr(i, "node_id", None)
            code = getattr(i, "code", None)
            msg = getattr(i, "message", None)
            if node_id is not None and code is not None and msg is not None:
                print(f"- {node_id} [{code}] {msg}")
            else:
                print(f"- {i!r}")
        return 2

    print("OK")
    rp = ui.get("resume_pick")
    if rp is not None:
        print(f"Resume next: {rp!r}")

    proposals = ui.get("scaffold_proposals") or {}
    if proposals:
        print("Scaffold proposals:")
        for goal_id in sorted(proposals.keys()):
            items = proposals[goal_id]
            print(f"- {goal_id}: {len(items)} proposal(s)")
            for p in items:
                print(
                    f"  - {p.scaffold_id}: "
                    f"{len(p.proposed_nodes)} node(s), "
                    f"{len(p.proposed_edges)} edge(s)"
                )
    return 0



def cmd_normalize(args: argparse.Namespace) -> int:
    normalize_dir(Path(args.data_dir))
    print("OK (normalized)")
    return 0


def cmd_append_set_state(args: argparse.Namespace) -> int:
    from .events import append_set_state_event
    from .loader_json import load_nodes_edges_from_dir

    data_dir = Path(args.data_dir)
    nodes, edges = load_nodes_edges_from_dir(data_dir)
    out_path = append_set_state_event(data_dir, nodes, edges)

    print(f"OK (appended SET_STATE to {out_path})")
    return 0


def cmd_materialize_events(args: argparse.Namespace) -> int:
    from .events import materialize_events_to_dir

    data_dir = Path(args.data_dir)
    materialized = materialize_events_to_dir(data_dir)

    print(
        f"OK (materialized {len(materialized.nodes)} nodes, "
        f"{len(materialized.edges)} edges from events.jsonl)"
    )
    return 0

def cmd_events_tail(args: argparse.Namespace) -> int:
    from collections import deque

    data_dir = Path(args.data_dir)
    events_path = data_dir / "events.jsonl"

    if args.limit < 1:
        if args.json:
            _print_json({"error": "limit must be >= 1"})
        else:
            print("limit must be >= 1")
        return 2

    if not events_path.is_file():
        result = {
            "events_jsonl": "missing",
            "showing": 0,
            "events": [],
        }
        if args.json:
            _print_json(result)
        else:
            print("events.jsonl: missing")
        return 1

    tail = deque(maxlen=args.limit)

    with events_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            tail.append(json.loads(line))

    summaries = []
    for ev in tail:
        ts = ev.get("ts", None)
        event_type = ev.get("type", "unknown")
        version = ev.get("v", None)

        summary = {
            "ts": ts,
            "type": event_type,
            "v": version,
        }

        if event_type == "SET_STATE":
            payload = ev.get("payload", {})
            nodes = payload.get("nodes", [])
            edges = payload.get("edges", [])

            if isinstance(nodes, list):
                summary["nodes"] = len(nodes)
            if isinstance(edges, list):
                summary["edges"] = len(edges)

        summaries.append(summary)

    result = {
        "events_jsonl": "present",
        "showing": len(summaries),
        "events": summaries,
    }

    if args.json:
        _print_json(result)
    else:
        print("events.jsonl: present")
        print(f"showing last {len(summaries)} event(s)")
        for idx, ev in enumerate(summaries, start=1):
            extra = ""
            if "nodes" in ev and "edges" in ev:
                extra = f" nodes={ev['nodes']} edges={ev['edges']}"
            print(f"[{idx}] ts={ev['ts']} type={ev['type']} v={ev['v']}{extra}")

    return 0

def cmd_replay_summary(args: argparse.Namespace) -> int:
    from .events import replay_summary

    summary = replay_summary(Path(args.data_dir), until_ts=args.until_ts)

    print(f"events.jsonl: {summary['events_jsonl']}")
    print(f"events: {summary['events']}")
    print(f"last_event_ts: {summary['last_event_ts']}")
    print(f"state_nodes: {summary['state_nodes']}")
    print(f"state_edges: {summary['state_edges']}")
    print(f"regime: {summary['regime']}")
    print(f"until_ts: {summary['until_ts']}")
    return 0



def cmd_compact_events(args: argparse.Namespace) -> int:
    from .events import compact_events_in_dir

    data_dir = Path(args.data_dir)
    out_path = compact_events_in_dir(data_dir)

    print(f"OK (compacted events log to {out_path})")
    return 0


def cmd_export_event_fixture(args: argparse.Namespace) -> int:
    from .events import export_event_fixture

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)

    export_event_fixture(
        source_dir,
        out_dir,
        include_materialized_snapshot=not args.events_only,
    )

    print(f"OK (exported event fixture to {out_dir})")
    return 0

def cmd_apply_scaffold(args: argparse.Namespace) -> int:
    from .state_provider import load_state
    from .knowledge.registry import load_knowledge_registry
    from .knowledge.apply import (
        resolve_scaffold_application,
        validate_scaffold_application,
    )
    from .events import append_apply_scaffold_proposal_event

    data_dir = Path(args.data_dir)

    loaded = load_state(
        data_dir,
        regime=args.state_regime,
        until_ts=args.until_ts,
    )
    knowledge_registry = load_knowledge_registry(data_dir)

    resolved = resolve_scaffold_application(
        loaded.nodes,
        goal_id=args.goal_id,
        scaffold_id=args.scaffold_id,
        knowledge_registry=knowledge_registry,
    )
    validate_scaffold_application(loaded.nodes, loaded.edges, resolved)

    out_path = append_apply_scaffold_proposal_event(
        data_dir,
        goal_id=resolved.goal_id,
        scaffold_id=resolved.scaffold_id,
        source_domain=resolved.source_domain,
        evidence_strength=resolved.evidence_strength,
        proposed_nodes=list(resolved.proposed_nodes),
        proposed_edges=list(resolved.proposed_edges),
    )

    print(
        f"OK (applied scaffold {resolved.scaffold_id} to {resolved.goal_id}: "
        f"{len(resolved.proposed_nodes)} node(s), "
        f"{len(resolved.proposed_edges)} edge(s) in {out_path})"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mttt")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser(
        "check",
        help="Run full compiler gate on authoritative state",
        description=(
            "Run invariants, lint, and resume selection on authoritative state. "
            "Authority is selected via --state-regime."
        ),
    )
    c.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing canonical state files",
    )
    c.add_argument(
        "--preferred-domain",
        default=None,
        help="Optional domain preference for resume ranking",
    )
    c.add_argument(
        "--state-regime",
        choices=["snapshot", "events"],
        default="snapshot",
        help=(
            "Authoritative state source: "
            "'snapshot' loads nodes.json/edges.json; "
            "'events' replays events.jsonl."
        ),
    )
    c.add_argument(
        "--until-ts",
        type=int,
        default=None,
        help=(
            "For event regime only: replay only events with ts <= this value. "
             "Ignored in snapshot regime."
        ),
    )
    c.add_argument(
            "--with-knowledge",
            action="store_true",
            help=(
                "Load knowledge_events.jsonl from data-dir and emit scaffold proposals "
                "for recoverable decomposition gaps."
            )
        )
    c.set_defaults(func=cmd_check)
    
    h = sub.add_parser(
        "events-head",
        help="Show basic information about the events log (count and timestamp range)",
        description=(
            "Read events.jsonl and print basic information about the log "
            "without replaying state."
        ),
    )
    h.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing events.jsonl",
    )
    h.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text",
    )
    h.set_defaults(func=cmd_events_head)

    t = sub.add_parser(
        "events-tail",
        help="Show the last N events from events.jsonl",
        description=(
            "Read events.jsonl and print a compact summary of the last N events "
            "without replaying state."
        ),
    )
    t.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text",
    )
    t.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing events.jsonl",
    )
    t.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of trailing events to show",
    )
    t.set_defaults(func=cmd_events_tail)

    n = sub.add_parser(
        "normalize",
        help="Rewrite nodes.json/edges.json deterministically",
        description=(
            "Normalize snapshot-authoritative state files "
            "(nodes.json / edges.json) deterministically."
        ),
    )
    n.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing nodes.json and edges.json",
    )
    n.set_defaults(func=cmd_normalize)

    a = sub.add_parser(
        "append-set-state",
        help="Append snapshot state as one SET_STATE event",
        description=(
            "Read canonical snapshot state from nodes.json / edges.json "
            "and append one SET_STATE event to events.jsonl."
        ),
    )
    a.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing canonical state files",
    )
    a.set_defaults(func=cmd_append_set_state)

    m = sub.add_parser(
        "materialize-events",
        help="Replay event-authoritative state into snapshot files",
        description=(
            "Replay events.jsonl and write canonical nodes.json / edges.json."
        ),
    )
    m.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing events.jsonl",
    )
    m.set_defaults(func=cmd_materialize_events)

    k = sub.add_parser(
        "compact-events",
        help="Replay events.jsonl and rewrite it as one canonical SET_STATE event",
        description=(
            "Replay event-authoritative state and compact the log to a single "
            "canonical SET_STATE event."
        ),
    )
    k.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing events.jsonl",
    )
    k.set_defaults(func=cmd_compact_events)
    
    p_apply = sub.add_parser(
        "apply-scaffold",
        help="Append authoritative scaffold application event",
    )
    p_apply.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing canonical state files",
    )
    p_apply.add_argument("--goal-id", required=True)
    p_apply.add_argument("--scaffold-id", required=True)
    p_apply.add_argument(
        "--state-regime",
        default="snapshot",
        choices=["snapshot", "events"],
        help=(
            "Authoritative state source: 'snapshot' loads nodes.json/edges.json; "
            "'events' replays events.jsonl."
        ),
    )
    p_apply.set_defaults(func=cmd_apply_scaffold)

    r = sub.add_parser(
        "replay-summary",
        help="Print a compact summary of events.jsonl and replayed end state",
        description=(
            "Load events.jsonl, replay event-authoritative state, and print a "
            "small summary of the log and replayed end state."
        ),
    )
    r.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing events.jsonl",
    )
    r.add_argument(
        "--until-ts",
        type=int,
        default=None,
        help="Replay only events with ts <= this value",
    )
    r.set_defaults(func=cmd_replay_summary)

    x = sub.add_parser(
        "export-event-fixture",
        help="Create a canonical event fixture directory from snapshot state",
        description=(
            "Read canonical snapshot state from source-dir and create an "
            "event-authoritative fixture in out-dir."
        ),
    )
    x.add_argument(
        "--source-dir",
        default="fixtures/valid_minimal",
        help="Directory containing canonical snapshot files",
    )
    x.add_argument(
        "--out-dir",
        required=True,
        help="Directory to write the event fixture into",
    )
    x.add_argument(
        "--events-only",
        action="store_true",
        help="Write only events.jsonl, without materialized nodes.json / edges.json",
    )
    x.set_defaults(func=cmd_export_event_fixture)

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return int(args.func(args))

def cmd_apply_scaffold(args: argparse.Namespace) -> int:
    from pathlib import Path

    from .state_provider import load_state
    from .knowledge.registry import load_knowledge_registry
    from .knowledge.apply import resolve_scaffold_application, validate_scaffold_application
    from .events import append_apply_scaffold_event

    data_dir = Path(args.data_dir)

    loaded = load_state(
        data_dir=data_dir,
        regime=args.state_regime,
    )

    knowledge_registry = load_knowledge_registry(data_dir)

    resolved = resolve_scaffold_application(
        loaded.nodes,
        goal_id=args.goal_id,
        scaffold_id=args.scaffold_id,
        knowledge_registry=knowledge_registry,
    )

    validate_scaffold_application(loaded.nodes, loaded.edges, resolved)

    append_apply_scaffold_event(
        data_dir=data_dir,
        nodes=list(resolved.proposed_nodes),
    edges=list(resolved.proposed_edges),
    )

    print(
        f"OK (applied scaffold {resolved.scaffold_id} to {resolved.goal_id}: "
        f"{len(resolved.proposed_nodes)} nodes, {len(resolved.proposed_edges)} edges)"
    )
    return 0




if __name__ == "__main__":
    raise SystemExit(main())
