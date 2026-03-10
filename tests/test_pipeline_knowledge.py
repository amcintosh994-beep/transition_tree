from __future__ import annotations

import unittest

from mttt.knowledge.model import NodeTemplate, Scaffold
from mttt.knowledge.registry import registry_from_scaffolds
from mttt.model import Kind
from mttt.pipeline import compute_ui_state
from tests.fixtures import (
    fixture_invalid_goal_no_decomp,
    fixture_invalid_task_missing_estimate,
)


class TestPipelineKnowledge(unittest.TestCase):
    def test_pipeline_recovers_e022_into_scaffold_proposals(self) -> None:
        nodes, edges = fixture_invalid_goal_no_decomp()

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
        registry = registry_from_scaffolds([scaffold])

        ui = compute_ui_state(
            nodes,
            edges,
            knowledge_registry=registry,
        )

        self.assertFalse(ui["ok"])
        self.assertTrue(ui["recoverable"])
        self.assertIsNotNone(ui["derived"])
        self.assertIn("G2", ui["scaffold_proposals"])
        self.assertEqual(len(ui["scaffold_proposals"]["G2"]), 1)

    def test_pipeline_does_not_recover_non_e022_failures(self) -> None:
        nodes, edges = fixture_invalid_task_missing_estimate()

        scaffold = Scaffold(
            scaffold_id="scaf_voice_001",
            domain="voice",
            match_terms=("voice",),
            entrypoint_template_indices=(0,),
            node_templates=(
                NodeTemplate(
                    kind=Kind.TASK,
                    text_template="Do choose one first step for {goal_tail}.",
                    default_domain="voice",
                    default_est_minutes=10,
                ),
            ),
            priority=10,
        )
        registry = registry_from_scaffolds([scaffold])

        ui = compute_ui_state(
            nodes,
            edges,
            knowledge_registry=registry,
        )

        self.assertFalse(ui["ok"])
        self.assertFalse(ui["recoverable"])
        self.assertIsNone(ui["derived"])
        self.assertEqual(ui["scaffold_proposals"], {})
