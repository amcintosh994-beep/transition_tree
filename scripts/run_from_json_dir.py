# run_from_json_dir.py
from __future__ import annotations

import sys
from loader_json import load_nodes_edges_from_dir
from pipeline import compute_ui_state


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python run_from_json_dir.py <dir_with_nodes_and_edges_json>")
        return 2

    dir_path = sys.argv[1]
    nodes, edges = load_nodes_edges_from_dir(dir_path)

    ui = compute_ui_state(nodes, edges, preferred_domain=None, fast_fail=True)

    if not ui["ok"]:
        print(ui["invariants"].to_text())
        if "cnl_issues" in ui and ui["cnl_issues"]:
            print("\nCNL lint issues:")
            for i in ui["cnl_issues"]:
                print(f"- [{i.code}] {i.severity} node={i.node_id}: {i.message}")
        return 1

    print(ui["invariants"].to_text())
    if ui.get("cnl_issues"):
        cnl_warns = [i for i in ui["cnl_issues"] if i.severity == "WARN"]
        if cnl_warns:
            print("\nCNL warnings:")
            for i in cnl_warns:
                print(f"- [{i.code}] node={i.node_id}: {i.message}")

    pick = ui["resume_pick"]
    if pick is None:
        print("\nResume: no actionable tasks.")
    else:
        print(f"\nResume: {pick.node_id} ({pick.reason})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
