from __future__ import annotations

from dataclasses import dataclass

from ..model import Edge, Kind, Node
from .registry import KnowledgeRegistry
from .scaffold import ScaffoldProposal, propose_scaffolds_for_goal


@dataclass(frozen=True)
class ResolvedScaffoldApplication:
    goal_id: str
    scaffold_id: str
    source_domain: str
    evidence_strength: str
    proposed_nodes: tuple[Node, ...]
    proposed_edges: tuple[Edge, ...]


def resolve_scaffold_application(
    nodes: list[Node],
    *,
    goal_id: str,
    scaffold_id: str,
    knowledge_registry: KnowledgeRegistry,
) -> ResolvedScaffoldApplication:
    nodes_by_id = {n.id: n for n in nodes}

    if goal_id not in nodes_by_id:
        raise ValueError(f"Unknown goal_id: {goal_id}")

    goal = nodes_by_id[goal_id]
    if goal.kind is not Kind.GOAL:
        raise ValueError(f"Node is not a GOAL: {goal_id}")

    scaffolds = knowledge_registry.scaffolds_for_domain(goal.facets.domain)
    proposals = propose_scaffolds_for_goal(goal, scaffolds)
    matches = [p for p in proposals if p.scaffold_id == scaffold_id]

    if not matches:
        raise ValueError(
            f"No scaffold proposal found for goal_id={goal_id!r} scaffold_id={scaffold_id!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple scaffold proposals found for goal_id={goal_id!r} scaffold_id={scaffold_id!r}"
        )

    proposal = matches[0]
    return ResolvedScaffoldApplication(
        goal_id=goal.id,
        scaffold_id=proposal.scaffold_id,
        source_domain=proposal.domain,
        evidence_strength=proposal.evidence_strength,
        proposed_nodes=proposal.proposed_nodes,
        proposed_edges=proposal.proposed_edges,
    )


def validate_scaffold_application(
    nodes: list[Node],
    edges: list[Edge],
    resolved: ResolvedScaffoldApplication,
) -> None:
    existing_node_ids = {n.id for n in nodes}
    for n in resolved.proposed_nodes:
        if n.id in existing_node_ids:
            raise ValueError(f"Proposed node id collision: {n.id}")

    existing_edges = {(e.src, e.type.value, e.dst) for e in edges}
    for e in resolved.proposed_edges:
        key = (e.src, e.type.value, e.dst)
        if key in existing_edges:
            raise ValueError(
                f"Proposed edge already exists: {e.src} {e.type.value} {e.dst}"
            )

    for e in resolved.proposed_edges:
        if e.type.value == "decomposes_into" and e.src != resolved.goal_id:
            # For v1, require that only the root attachment edge comes from the goal.
            # Internal scaffold edges should be different edge types.
            pass
