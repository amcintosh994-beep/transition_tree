from __future__ import annotations

import unittest

from mttt.knowledge.model import DependencyTemplate, NodeTemplate, Scaffold
from mttt.knowledge.scaffold import propose_scaffolds_for_goal
from mttt.model import EdgeType, Facets, Kind, Node, Status


class TestKnowledgeScaffold(unittest.TestCase):
    def test_propose_scaffolds_for_goal_emits_goal_attachment_and_lint_valid_nodes(self) -> None:
        goal = Node(
            id="G2",
            kind=Kind.GOAL,
            text="Achieve a consistent skincare routine.",
            slots={},
            facets=Facets(status=Status.ACTIVE, domain="care"),
        )

        scaffold = Scaffold(
            scaffold_id="scaf_skin_001",
            domain="care",
            match_terms=("skincare",),
            entrypoint_template_indices=(0,),
            node_templates=(
                NodeTemplate(
                    kind=Kind.TASK,
                    text_template="Do list one first step for {goal_tail}.",
                    default_domain="care",
                    default_est_minutes=10,
                ),
                NodeTemplate(
                    kind=Kind.TASK,
                    text_template="Do schedule one repeatable time for {goal_tail}.",
                    default_domain="care",
                    default_est_minutes=10,
                ),
            ),
            dependency_templates=(
                DependencyTemplate(
                    src_index=1,
                    edge_type=EdgeType.REQUIRES_TASK,
                    dst_index=0,
                ),
            ),
            priority=10,
        )

        proposals = propose_scaffolds_for_goal(goal, (scaffold,))

        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.scaffold_id, "scaf_skin_001")
        self.assertEqual(len(proposal.proposed_nodes), 2)
        self.assertEqual(len(proposal.proposed_edges), 2)

        first_edge = proposal.proposed_edges[0]
        self.assertEqual(first_edge.src, "G2")
        self.assertEqual(first_edge.type, EdgeType.DECOMPOSES_INTO)
