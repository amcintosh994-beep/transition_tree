from __future__ import annotations

import argparse
from pathlib import Path

from .normalize_json import normalize_dir
from .pipeline import compute_ui_state

def cmd_check(args: argparse.Namespace) -> int:
    from pathlib import Path

    from .pipeline import compute_ui_state
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

    return p



def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
