# resume_ranking.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from mttt_model import Node
from derived_status import DerivedState


@dataclass(frozen=True)
class ResumePick:
    node_id: str
    reason: str


def rank_resume_candidates(
    nodes_by_id: Dict[str, Node],
    derived: Dict[str, DerivedState],
    *,
    preferred_domain: Optional[str] = None,
) -> List[str]:
    """
    Returns candidate TASK ids sorted best->worst.
    Deterministic ordering.
    """
    candidates: List[Node] = []
    for nid, ds in derived.items():
        if ds.is_actionable_task:
            candidates.append(nodes_by_id[nid])

    def sort_key(n: Node) -> Tuple[int, int, int, str]:
        # domain preference: 0 preferred, 1 otherwise
        dom_penalty = 0
        if preferred_domain is not None:
            dom_penalty = 0 if (n.facets.domain == preferred_domain) else 1

        # est_minutes: unknown = large sentinel
        est = n.facets.est_minutes if n.facets.est_minutes is not None else 10**9

        # maintenance_mode tasks slightly deprioritized unless preferred_domain matches
        maint_penalty = 1 if (n.facets.status.value == "maintenance_mode") else 0

        return (dom_penalty, est, maint_penalty, n.id)

    return [n.id for n in sorted(candidates, key=sort_key)]


def pick_resume_next(
    nodes_by_id: Dict[str, Node],
    derived: Dict[str, DerivedState],
    *,
    preferred_domain: Optional[str] = None,
) -> Optional[ResumePick]:
    ranked = rank_resume_candidates(nodes_by_id, derived, preferred_domain=preferred_domain)
    if not ranked:
        return None

    top = ranked[0]
    n = nodes_by_id[top]
    reason = "Next actionable task"
    if preferred_domain and n.facets.domain == preferred_domain:
        reason = f"Next actionable task in preferred domain: {preferred_domain}"
    return ResumePick(node_id=top, reason=reason)
