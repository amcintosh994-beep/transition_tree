# pipeline.py
from __future__ import annotations
from typing import List, Optional
from .model import Edge, Node
from .invariants import check_invariants
from .cnl_lint import lint_cnl
from .derived_status import compute_derived_states
from .resume_ranking import pick_resume_next
def compute_ui_state(
    nodes: List[Node],
    edges: List[Edge],
    *,
    preferred_domain: Optional[str] = None,
    fast_fail: bool = True,
):
    # --- INVARIANTS ---
    report = check_invariants(nodes, edges, fast_fail=fast_fail)
    if not report.ok:
        return {
            "ok": False,
            "invariants": report,
            "cnl_issues": [],
            "derived": None,
            "resume_pick": None,
        }
    # --- CNL LINT ---
    cnl_issues = lint_cnl(nodes)
    cnl_errors = [i for i in cnl_issues if i.severity == "ERROR"]
    if cnl_errors:
        return {
            "ok": False,
            "invariants": report,
            "cnl_issues": cnl_issues,
            "derived": None,
            "resume_pick": None,
        }
    # --- DERIVED STATE ---
    derived = compute_derived_states(nodes, edges)
    # --- RESUME RANKING ---
    nodes_by_id = {n.id: n for n in nodes}
    resume_pick = pick_resume_next(nodes_by_id, derived, preferred_domain=preferred_domain)
    return {
        "ok": True,
        "invariants": report,
        "cnl_issues": cnl_issues,
        "derived": derived,
        "resume_pick": resume_pick,
    }



