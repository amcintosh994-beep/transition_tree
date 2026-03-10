# pipeline.py
from __future__ import annotations

from typing import List, Optional

from .model import Edge, Node
from .invariants import InvariantCodes, check_invariants
from .cnl_lint import lint_cnl
from .derived_status import compute_derived_states
from .resume_ranking import pick_resume_next


def _recoverable_goal_decomposition_only(report) -> bool:
    if report is None or report.ok:
        return False
    if not report.errors:
        return False
    return all(e.code == InvariantCodes.GOAL_WITHOUT_DECOMPOSITION for e in report.errors)


def _build_scaffold_proposals(nodes, derived, knowledge_registry):
    if knowledge_registry is None or derived is None:
        return {}

    from .knowledge.scaffold import propose_scaffolds_for_goal

    nodes_by_id = {n.id: n for n in nodes}
    out = {}

    for node_id in sorted(derived.keys()):
        ds = derived[node_id]
        if not ds.needs_decomposition:
            continue
        goal = nodes_by_id[node_id]
        proposals = propose_scaffolds_for_goal(
            goal,
            knowledge_registry.scaffolds_for_domain(goal.facets.domain),
        )
        if proposals:
            out[node_id] = proposals

    return out


def compute_ui_state(
    nodes: List[Node],
    edges: List[Edge],
    *,
    preferred_domain: Optional[str] = None,
    fast_fail: bool = True,
    knowledge_registry=None,
):
    # --- INVARIANTS ---
    invariant_fast_fail = False if knowledge_registry is not None else fast_fail
    report = check_invariants(nodes, edges, fast_fail=invariant_fast_fail)
    recoverable = _recoverable_goal_decomposition_only(report)

    if not report.ok and not recoverable:
        return {
            "ok": False,
            "recoverable": False,
            "invariants": report,
            "cnl_issues": [],
            "derived": None,
            "resume_pick": None,
            "scaffold_proposals": {},
        }

    # --- CNL LINT ---
    cnl_issues = lint_cnl(nodes)
    cnl_errors = [i for i in cnl_issues if i.severity == "ERROR"]
    if cnl_errors:
        return {
            "ok": False,
            "recoverable": False,
            "invariants": report,
            "cnl_issues": cnl_issues,
            "derived": None,
            "resume_pick": None,
            "scaffold_proposals": {},
        }

    # --- DERIVED STATE ---
    derived = compute_derived_states(nodes, edges)
    scaffold_proposals = _build_scaffold_proposals(nodes, derived, knowledge_registry)

    if recoverable:
        return {
            "ok": False,
            "recoverable": True,
            "invariants": report,
            "cnl_issues": cnl_issues,
            "derived": derived,
            "resume_pick": None,
            "scaffold_proposals": scaffold_proposals,
        }

    # --- RESUME RANKING ---
    nodes_by_id = {n.id: n for n in nodes}
    resume_pick = pick_resume_next(nodes_by_id, derived, preferred_domain=preferred_domain)
    return {
        "ok": True,
        "recoverable": False,
        "invariants": report,
        "cnl_issues": cnl_issues,
        "derived": derived,
        "resume_pick": resume_pick,
        "scaffold_proposals": scaffold_proposals,
    }
