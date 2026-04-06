from __future__ import annotations
from mttt.events import append_set_state_event

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import dataclasses
import enum

def _to_jsonable(x):
    if dataclasses.is_dataclass(x):
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(x).items()}
    if isinstance(x, enum.Enum):
        return x.value
    if isinstance(x, dict):
        return {k: _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    return x



from mttt.cli import cmd_apply_scaffold
from mttt.knowledge.model import NodeTemplate, Scaffold
from mttt.knowledge.registry import load_knowledge_registry, registry_from_scaffolds
from mttt.model import Kind
from mttt.pipeline import compute_ui_state
from mttt.state_provider import load_state
from tests.fixtures import fixture_invalid_goal_no_decomp


class TestCliScaffoldFlow(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.data_dir = self.tmpdir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_apply_scaffold_resolves_recoverable_state(self) -> None:
        # --- Arrange: recoverable state from known-good fixture ---
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

        # Write canonical snapshot files
        (self.data_dir / "nodes.json").write_text(
            json.dumps([_to_jsonable(n) for n in nodes], indent=2),
            encoding="utf-8",
        )
        (self.data_dir / "edges.json").write_text(
            json.dumps([_to_jsonable(e) for e in edges], indent=2),
            encoding="utf-8",
        )

        # Seed event-authoritative baseline state
        append_set_state_event(self.data_dir, nodes, edges)

        # Write knowledge registry as knowledge_events.jsonl
        knowledge_event = {
            "ts": 1,
            "type": "KNOWLEDGE_SCAFFOLD_CONFIRMED",
            "v": 1,
            "payload": _to_jsonable(scaffold),
        }
        (self.data_dir / "knowledge_events.jsonl").write_text(
            json.dumps(knowledge_event) + "\n",
            encoding="utf-8",
        )
        # --- Assert precondition: recoverable before apply ---
        loaded = load_state(self.data_dir)
        loaded_registry = load_knowledge_registry(self.data_dir)

        ui = compute_ui_state(
            loaded.nodes,
            loaded.edges,
            knowledge_registry=loaded_registry,
        )

        self.assertFalse(ui["ok"])
        self.assertTrue(ui["recoverable"], "Expected recoverable state before scaffold")
        self.assertIn("G2", ui["scaffold_proposals"])
        self.assertEqual(len(ui["scaffold_proposals"]["G2"]), 1)

        # --- Apply scaffold via CLI ---
        args = type(
            "Args",
            (),
            {
                "data_dir": str(self.data_dir),
                "goal_id": "G2",
                "scaffold_id": "scaf_skin_001",
                "state_regime": "snapshot",
                "until_ts": None,
            },
        )()

        rc = cmd_apply_scaffold(args)
        self.assertEqual(rc, 0)

        # --- Reload and verify recoverable state is gone ---
        loaded2 = load_state(self.data_dir, regime="events")
        ui2 = compute_ui_state(
            loaded2.nodes,
            loaded2.edges,
            knowledge_registry=loaded_registry,
        )

        self.assertFalse(
            ui2["recoverable"],
            "Expected scaffold to resolve recoverable invariant",
        )
