from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.knowledge.events import append_scaffold_confirmed_event
from mttt.knowledge.model import NodeTemplate, Scaffold
from mttt.knowledge.registry import load_knowledge_registry
from mttt.model import Kind


class TestKnowledgeRegistry(unittest.TestCase):
    def test_load_knowledge_registry_indexes_scaffolds_by_domain(self) -> None:
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
            ),
            priority=10,
        )

        with tempfile.TemporaryDirectory(prefix="mttt_knowledge_registry_") as td:
            data_dir = Path(td)
            append_scaffold_confirmed_event(data_dir, scaffold, ts=1700000000)

            registry = load_knowledge_registry(data_dir)

            self.assertIn("scaf_skin_001", registry.scaffolds_by_id)
            self.assertEqual(len(registry.scaffolds_for_domain("care")), 1)
            self.assertEqual(registry.scaffolds_for_domain("voice"), ())
