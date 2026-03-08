from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import append_set_state_event
from mttt.loader_json import load_nodes_edges_from_dir
from mttt.state_provider import load_state


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestStateProvider(unittest.TestCase):
    def test_load_state_snapshot(self) -> None:
        loaded = load_state(FIXTURE_DIR, regime="snapshot")
        self.assertEqual(loaded.regime, "snapshot")
        self.assertTrue(len(loaded.nodes) > 0)
        self.assertTrue(len(loaded.edges) > 0)

    def test_load_state_events(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_provider_") as td:
            data_dir = Path(td)
            append_set_state_event(data_dir, nodes, edges, ts=1700000000)

            loaded = load_state(data_dir, regime="events")
            self.assertEqual(loaded.regime, "events")
            self.assertEqual(len(loaded.nodes), len(nodes))
            self.assertEqual(len(loaded.edges), len(edges))
