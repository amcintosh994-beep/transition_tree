from __future__ import annotations

from dataclasses import dataclass

from ..cnl_lint import lint_cnl
from ..model import Edge, EdgeType, Facets, Kind, Node, Status
from .model import Scaffold


@dataclass(frozen=True)
class ScaffoldProposal:
    scaffold_id: str
    domain: str
    evidence_strength: str
    proposed_nodes: tuple[Node, ...]
    proposed_edges: tuple[Edge, ...]


def _goal_tail(goal: Node) -> str:
    text = goal.text.strip()
    if text.endswith("."):
        text = text[:-1]
    if text.startswith("Achieve "):
        return text[len("Achieve "):]
    return text


def _matches_goal(goal: Node, scaffold: Scaffold) -> bool:
    if goal.facets.domain != scaffold.domain:
        return False

    if not scaffold.match_terms:
        return True

    haystack = goal.text.casefold()
    return any(term.casefold() in haystack for term in scaffold.match_terms)


def _instantiate_text(template: str, goal: Node) -> str:
    return template.format(
        goal_id=goal.id,
        goal_text=goal.text.strip(),
        goal_tail=_goal_tail(goal),
    )


def _instantiate_scaffold(goal: Node, scaffold: Scaffold) -> ScaffoldProposal | None:
    proposal_nodes: list[Node] = []
    proposal_edges: list[Edge] = []

    for idx, nt in enumerate(scaffold.node_templates):
        node_id = f"proposal::{goal.id}::{scaffold.scaffold_id}::N{idx}"
        text = _instantiate_text(nt.text_template, goal)
        node = Node(
            id=node_id,
            kind=nt.kind,
            text=text,
            slots={
                **nt.slots,
                "scaffold_id": scaffold.scaffold_id,
                "scaffold_source_goal": goal.id,
            },
            facets=Facets(
                status=Status.ACTIVE,
                domain=nt.default_domain or goal.facets.domain,
                est_minutes=nt.default_est_minutes,
            ),
        )
        proposal_nodes.append(node)

    lint_issues = lint_cnl(proposal_nodes)
    lint_errors = [i for i in lint_issues if i.severity == "ERROR"]
    if lint_errors:
        return None

    for idx in scaffold.entrypoint_template_indices:
        proposal_edges.append(
            Edge(
                src=goal.id,
                type=EdgeType.DECOMPOSES_INTO,
                dst=proposal_nodes[idx].id,
            )
        )

    for dep in scaffold.dependency_templates:
        proposal_edges.append(
            Edge(
                src=proposal_nodes[dep.src_index].id,
                type=dep.edge_type,
                dst=proposal_nodes[dep.dst_index].id,
            )
        )

    return ScaffoldProposal(
        scaffold_id=scaffold.scaffold_id,
        domain=scaffold.domain,
        evidence_strength=scaffold.evidence_strength,
        proposed_nodes=tuple(proposal_nodes),
        proposed_edges=tuple(proposal_edges),
    )


def propose_scaffolds_for_goal(
    goal: Node,
    scaffolds: tuple[Scaffold, ...],
) -> tuple[ScaffoldProposal, ...]:
    proposals: list[ScaffoldProposal] = []

    for scaffold in sorted(scaffolds, key=lambda x: (x.priority, x.scaffold_id)):
        if not _matches_goal(goal, scaffold):
            continue
        proposal = _instantiate_scaffold(goal, scaffold)
        if proposal is not None:
            proposals.append(proposal)

    return tuple(proposals)
