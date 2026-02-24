from __future__ import annotations

import unittest
from pathlib import Path

from loader_json import load_nodes_edges_from_dir
from pipeline import compute_ui_state


class TestResumeStability(unittest.TestCase):

    def test_resume_pick_is_stable(self):
        repo_root = Path(__file__).resolve().parents[1]
        fixture = repo_root / "fixtures" / "resume_simple"

        nodes, edges = load_nodes_edges_from_dir(fixture)

        state1 = compute_ui_state(nodes, edges, fast_fail=False)
        if not state1["ok"]:
            inv = state1["invariants"]
            inv_lines = []
            if not inv.ok:
                inv_lines = [f"{e.code}: {e.message}" for e in inv.errors]
            cnl_lines = [f"{i.code}: {i.message}" for i in state1["cnl_issues"] if i.severity == "ERROR"]
            self.fail("Gate failed.\nINVARIANTS:\n  " + "\n  ".join(inv_lines) + "\nCNL:\n  " + "\n  ".join(cnl_lines))
        pick1 = state1["resume_pick"]

        # Run again to assert stability
        nodes2, edges2 = load_nodes_edges_from_dir(fixture)
        state2 = compute_ui_state(nodes2, edges2, fast_fail=False)
        pick2 = state2["resume_pick"]

        self.assertIsNotNone(pick1)
        self.assertEqual(pick1, pick2)
        self.assertEqual(pick1.node_id, "T2")
        self.assertEqual(pick1.reason, "Next actionable task")