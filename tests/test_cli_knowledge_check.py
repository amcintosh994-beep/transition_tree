from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mttt.knowledge.events import append_scaffold_confirmed_event
from mttt.knowledge.model import NodeTemplate, Scaffold
from mttt.model import Kind
from mttt.normalize_json import save_nodes_edges_to_dir
from tests.fixtures import fixture_invalid_goal_no_decomp


class TestCliKnowledgeCheck(unittest.TestCase):
    def test_check_with_knowledge_prints_scaffold_proposals_on_recoverable_gap(self) -> None:
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

        with tempfile.TemporaryDirectory(prefix="mttt_cli_knowledge_") as td:
            data_dir = Path(td)
            save_nodes_edges_to_dir(data_dir, nodes, edges)
            append_scaffold_confirmed_event(data_dir, scaffold, ts=1700000000)

            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mttt.cli",
                    "check",
                    "--data-dir",
                    str(data_dir),
                    "--with-knowledge",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 2)
            self.assertIn("INVARIANTS FAILED", proc.stdout)
            self.assertIn("Scaffold proposals:", proc.stdout)
            self.assertIn("G2", proc.stdout)
            self.assertIn("scaf_skin_001", proc.stdout)
