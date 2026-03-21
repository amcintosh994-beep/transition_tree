from __future__ import annotations

import unittest

from mttt.knowledge.model import NodeTemplate, Scaffold
from mttt.model import Kind


class TestKnowledgeScaffoldDomainValidation(unittest.TestCase):
    def test_scaffold_rejects_invalid_domain(self) -> None:
        with self.assertRaises(ValueError) as cm:
            Scaffold(
                scaffold_id="scaf_invalid_domain_001",
                domain="made_up_domain",
                match_terms=("test",),
                entrypoint_template_indices=(0,),
                node_templates=(
                    NodeTemplate(
                        kind=Kind.TASK,
                        text_template="Do one valid step for {goal_tail}.",
                        default_domain="care",
                        default_est_minutes=10,
                    ),
                ),
                priority=10,
            )

        self.assertIn("Scaffold.domain", str(cm.exception))
        self.assertIn("made_up_domain", str(cm.exception))

    def test_node_template_rejects_invalid_default_domain(self) -> None:
        with self.assertRaises(ValueError) as cm:
            NodeTemplate(
                kind=Kind.TASK,
                text_template="Do one valid step for {goal_tail}.",
                default_domain="not_a_real_domain",
                default_est_minutes=10,
            )

        self.assertIn("NodeTemplate.default_domain", str(cm.exception))
        self.assertIn("not_a_real_domain", str(cm.exception))
