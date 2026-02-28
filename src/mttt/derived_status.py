# derived_status.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .model import Edge, EdgeType, Kind, Node, Status


@dataclass(frozen=True)
class DerivedState:
    node_id: str
    kind: Kind
    status: Status

    # Computed flags
    is_completed: bool
    is_parked: bool
    is_blocked: bool
    is_actionable_task: bool

    # Explanations (stable, UI-friendly)
    unsatisfied_requires_task: List[str]
    unsatisfied_requires_asset: List[str]
    active_blockers: List[str]  # blocker node ids
    needs_decomposition: bool
    needs_discharge: bool


def _index(nodes: List[Node]) -> Dict[str, Node]:
    return {n.id: n for n in nodes}


def _edges_by_type(edges: List[Edge], et: EdgeType) -> List[Edge]:
    return [e for e in edges if e.type == et]


def compute_derived_states(nodes: List[Node], edges: List[Edge]) -> Dict[str, DerivedState]:
    """
    Deterministic derived-state computation.
    Assumes invariants already passed (or else results may be misleading).
    """
    nodes_by_id = _index(nodes)

    requires_task = _edges_by_type(edges, EdgeType.REQUIRES_TASK)
    requires_asset = _edges_by_type(edges, EdgeType.REQUIRES_ASSET)
    blocked_by = _edges_by_type(edges, EdgeType.BLOCKED_BY)
    decomp = _edges_by_type(edges, EdgeType.DECOMPOSES_INTO)
    answers = _edges_by_type(edges, EdgeType.ANSWERS)

    # Build quick lookups (sorted for determinism)
    req_task_by_src: Dict[str, List[str]] = {}
    req_asset_by_src: Dict[str, List[str]] = {}
    blockers_by_src: Dict[str, List[str]] = {}
    decomp_by_goal: Dict[str, List[str]] = {}
    answers_in_question: Dict[str, List[str]] = {}

    for e in sorted(requires_task, key=lambda x: (x.src, x.dst)):
        req_task_by_src.setdefault(e.src, []).append(e.dst)
    for e in sorted(requires_asset, key=lambda x: (x.src, x.dst)):
        req_asset_by_src.setdefault(e.src, []).append(e.dst)
    for e in sorted(blocked_by, key=lambda x: (x.src, x.dst)):
        blockers_by_src.setdefault(e.src, []).append(e.dst)
    for e in sorted(decomp, key=lambda x: (x.src, x.dst)):
        decomp_by_goal.setdefault(e.src, []).append(e.dst)
    for e in sorted(answers, key=lambda x: (x.src, x.dst)):
        answers_in_question.setdefault(e.dst, []).append(e.src)

    out: Dict[str, DerivedState] = {}

    def is_done(nid: str) -> bool:
        return nodes_by_id[nid].facets.status == Status.COMPLETED

    # We treat ASSET satisfied iff node completed (you can refine later).
    def asset_satisfied(aid: str) -> bool:
        return is_done(aid)

    for n in sorted(nodes, key=lambda x: x.id):
        nid = n.id
        st = n.facets.status
        is_completed = st == Status.COMPLETED
        is_parked = st == Status.PARKED

        unsat_tasks = [t for t in req_task_by_src.get(nid, []) if not is_done(t)]
        unsat_assets = [a for a in req_asset_by_src.get(nid, []) if not asset_satisfied(a)]

        active_blockers = []
        for bid in blockers_by_src.get(nid, []):
            # blocker considered active unless it is completed OR explicitly cleared in slots
            bnode = nodes_by_id[bid]
            if bnode.facets.status != Status.COMPLETED and bnode.slots.get("cleared", "").lower() != "true":
                active_blockers.append(bid)

        needs_decomposition = (n.kind == Kind.GOAL) and (nid not in decomp_by_goal) and (n.slots.get("is_root", "").lower() != "true")
        needs_discharge = (n.kind == Kind.QUESTION) and is_completed and (nid not in answers_in_question) and (n.slots.get("discharged", "").lower() != "true")

        is_blocked = (len(active_blockers) > 0) or (len(unsat_tasks) > 0) or (len(unsat_assets) > 0)

        is_actionable_task = (
            (n.kind == Kind.TASK)
            and (not is_completed)
            and (not is_parked)
            and (not is_blocked)
            and (st in {Status.ACTIVE, Status.MAINTENANCE_MODE})
        )

        out[nid] = DerivedState(
            node_id=nid,
            kind=n.kind,
            status=st,
            is_completed=is_completed,
            is_parked=is_parked,
            is_blocked=is_blocked,
            is_actionable_task=is_actionable_task,
            unsatisfied_requires_task=unsat_tasks,
            unsatisfied_requires_asset=unsat_assets,
            active_blockers=active_blockers,
            needs_decomposition=needs_decomposition,
            needs_discharge=needs_discharge,
        )

    return out



