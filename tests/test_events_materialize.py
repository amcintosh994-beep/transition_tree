from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import append_set_state_event, materialize_events_to_dir
from mttt.loader_json import load_nodes_edges_from_dir

FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestEventsMaterialize(unittest.TestCase):
    def test_materialize_events_writes_canonical_snapshot_files(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_materialize_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            materialized = materialize_events_to_dir(data_dir)

            self.assertEqual(len(materialized.nodes), len(nodes))
            self.assertEqual(len(materialized.edges), len(edges))

            nodes_path = data_dir / "nodes.json"
            edges_path = data_dir / "edges.json"

            self.assertTrue(nodes_path.is_file())
            self.assertTrue(edges_path.is_file())

            nodes_raw = nodes_path.read_text(encoding="utf-8")
            edges_raw = edges_path.read_text(encoding="utf-8")

            self.assertNotIn("\r", nodes_raw)
            self.assertNotIn("\r", edges_raw)
            self.assertTrue(nodes_raw.endswith("\n"))
            self.assertTrue(edges_raw.endswith("\n"))

    def test_materialized_snapshot_reloads_successfully(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_materialize_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            materialize_events_to_dir(data_dir)

            loaded_nodes, loaded_edges = load_nodes_edges_from_dir(data_dir)
            self.assertEqual(len(loaded_nodes), len(nodes))
            self.assertEqual(len(loaded_edges), len(edges))
