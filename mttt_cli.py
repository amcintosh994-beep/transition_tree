from __future__ import annotations

import argparse
import sys
from normalize_json import normalize_dir
from pathlib import Path

from loader_json import load_nodes_edges_from_dir, LoadError
from pipeline import compute_ui_state


def cmd_check(args: argparse.Namespace) -> int:
    try:
        nodes, edges = load_nodes_edges_from_dir(args.data_dir)
    except LoadError as e:
        print(f"LOAD ERROR: {e}", file=sys.stderr)
        return 3

    state = compute_ui_state(
        nodes,
        edges,
        preferred_domain=args.preferred_domain,
        fast_fail=False,
    )

    if not state["ok"]:
        print("COMPILER GATE FAILED", file=sys.stderr)

        inv = state["invariants"]
        if not inv.ok:
            for e in inv.errors:
                print(f"[INVARIANT] {e.code}: {e.message}", file=sys.stderr)

        for issue in state["cnl_issues"]:
            if issue.severity == "ERROR":
                print(f"[CNL] {issue.code}: {issue.message}", file=sys.stderr)

        return 2

    print("OK")
    if state["resume_pick"]:
        print(f"Resume next: {state['resume_pick']}")
    return 0

def cmd_normalize(args: argparse.Namespace) -> int:
    try:
        # normalize_dir will load via loader_json and rewrite deterministically
        normalize_dir(args.data_dir)
    except Exception as e:
        print(f"NORMALIZE ERROR: {e}", file=sys.stderr)
        return 4

    print("OK (normalized)")
    return 0

def main() -> int:
    p = argparse.ArgumentParser(prog="mttt")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Run full compiler gate")
    n = sub.add_parser("normalize", help="Rewrite nodes.json/edges.json deterministically")
    n.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing nodes.json and edges.json",
    )
    n.set_defaults(func=cmd_normalize)
    c.add_argument(
        "--data-dir",
        default="fixtures/valid_minimal",
        help="Directory containing nodes.json and edges.json",
    )
    c.add_argument(
        "--preferred-domain",
        default=None,
        help="Optional domain preference for resume ranking",
    )
    c.set_defaults(func=cmd_check)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())