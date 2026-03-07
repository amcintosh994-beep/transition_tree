from __future__ import annotations

import argparse
from pathlib import Path

from .normalize_json import normalize_dir
from .pipeline import compute_ui_state


def cmd_check(args: argparse.Namespace) -> int:
    from .state_provider import load_state

    loaded = load_state(
        Path(args.data_dir),
        regime=args.state_regime,
    )

    ui = compute_ui_state(
        loaded.nodes,
        loaded.edges,
        preferred_domain=args.preferred_domain,
    )

    inv = ui.get("invariants")
    if inv is not None and not getattr(inv, "ok", True):
        print("INVARIANTS FAILED")
        for e in getattr(inv, "errors", []):
            print(f"- {e}")
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mttt")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Run full compiler gate")
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
        help="How authoritative state is acquired",
    )
    c.set_defaults(func=cmd_check)

    n = sub.add_parser("normalize", help="Rewrite nodes.json/edges.json deterministically")
    n.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing nodes.json and edges.json",
    )
    n.set_defaults(func=cmd_normalize)

    a = sub.add_parser(
        "append-set-state",
        help="Append current snapshot state as one SET_STATE event to events.jsonl",
    )
    a.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing canonical state files",
    )
    a.set_defaults(func=cmd_append_set_state)
    
    m = sub.add_parser(
        "materialize-events",
        help="Replay events.jsonl and write canonical nodes.json / edges.json",
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
    )
    k.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing events.jsonl",
    )
    k.set_defaults(func=cmd_compact_events)

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return int(args.func(args))

def cmd_materialize_events(args: argparse.Namespace) -> int:
    from .events import materialize_events_to_dir

    data_dir = Path(args.data_dir)
    materialized = materialize_events_to_dir(data_dir)

    print(
        f"OK (materialized {len(materialized.nodes)} nodes, "
        f"{len(materialized.edges)} edges from events.jsonl)"
    )
    return 0

def cmd_compact_events(args: argparse.Namespace) -> int:
    from .events import compact_events_in_dir

    data_dir = Path(args.data_dir)
    out_path = compact_events_in_dir(data_dir)

    print(f"OK (compacted events log to {out_path})")
    return 0





if __name__ == "__main__":
    raise SystemExit(main())
