# tests/test_invariants_and_lint.py
from __future__ import annotations

import unittest
from mttt.cnl_lint import lint_cnl, CnlCodes
from mttt.invariants import check_invariants, InvariantCodes
from mttt.derived_status import compute_derived_states

from tests.fixtures import (
    fixture_valid_minimal,
    fixture_invalid_goal_no_decomp,
    fixture_invalid_task_missing_estimate,
    fixture_invalid_requires_task_cycle,
    fixture_invalid_cnl_template,
    fixture_invalid_conjunction_split_needed,
)


class TestCompilerGate(unittest.TestCase):
    def test_valid_minimal_passes(self):
        nodes, edges = fixture_valid_minimal()
        rep = check_invariants(nodes, edges, fast_fail=False)
        self.assertTrue(rep.ok, rep.to_text())
        issues = lint_cnl(nodes)
        self.assertTrue(all(i.severity != "ERROR" for i in issues), str(issues))
        derived = compute_derived_states(nodes, edges)
        self.assertTrue(
            any(v.is_actionable_task for v in derived.values()),
            "No actionable task found in derived state."
        )
        self.assertEqual(len(rep.errors), 0, rep.to_text())
        self.assertEqual(len(rep.warnings), 0, rep.to_text())

    def test_goal_without_decomposition_fails(self):
        nodes, edges = fixture_invalid_goal_no_decomp()
        rep = check_invariants(nodes, edges, fast_fail=False)
        self.assertFalse(rep.ok, rep.to_text())
        self.assertGreater(len(rep.errors), 0, "Expected invariant errors but none found.")
        self.assertTrue(
            any(e.code == InvariantCodes.GOAL_WITHOUT_DECOMPOSITION for e in rep.errors),
            f"Expected E022. Got: {[e.code for e in rep.errors]}",
        )

    def test_task_missing_estimate_fails(self):
        nodes, edges = fixture_invalid_task_missing_estimate()
        rep = check_invariants(nodes, edges, fast_fail=False)
        self.assertFalse(rep.ok)
        self.assertTrue(
            any(e.code == InvariantCodes.TASK_MISSING_ESTIMATE for e in rep.errors),
            f"Expected {InvariantCodes.TASK_MISSING_ESTIMATE}. Got: {[e.code for e in rep.errors]}",
        )
    def test_requires_task_cycle_fails(self):
        nodes, edges = fixture_invalid_requires_task_cycle()
        rep = check_invariants(nodes, edges, fast_fail=False)
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.code == InvariantCodes.REQUIRES_TASK_CYCLE for e in rep.errors))

    def test_cnl_template_mismatch_fails(self):
        nodes, edges = fixture_invalid_cnl_template()
        # invariants may pass, but CNL lint must fail
        rep = check_invariants(nodes, edges, fast_fail=False)
        self.assertTrue(rep.ok, rep.to_text())
        issues = lint_cnl(nodes)
        self.assertTrue(any(i.code == CnlCodes.TEXT_TEMPLATE_MISMATCH for i in issues))

    def test_conjunction_in_task_fails_cnl(self):
        nodes, edges = fixture_invalid_conjunction_split_needed()
        rep = check_invariants(nodes, edges, fast_fail=False)
        self.assertTrue(rep.ok, rep.to_text())
        issues = lint_cnl(nodes)
        self.assertTrue(any(i.code == CnlCodes.TEXT_FORBIDDEN_CONJUNCTION for i in issues))


if __name__ == "__main__":
    unittest.main()
