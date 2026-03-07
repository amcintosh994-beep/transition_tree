from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import export_event_fixture, load_and_replay_events
from mttt.loader_json import load_nodes_edges_from_dir


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestEventsExportFixture(unittest.TestCase):
    def test_export_event_fixture_writes_events_log_and_snapshot_files(self) -> None:
        source_nodes, source_edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_export_fixture_") as td:
            out_dir = Path(td) / "valid_minimal_events"

            export_event_fixture(FIXTURE_DIR, out_dir, ts=1700000000)

            self.assertTrue((out_dir / "events.jsonl").is_file())
            self.assertTrue((out_dir / "nodes.json").is_file())
            self.assertTrue((out_dir / "edges.json").is_file())

            materialized = load_and_replay_events(out_dir)
            self.assertEqual(len(materialized.nodes), len(source_nodes))
            self.assertEqual(len(materialized.edges), len(source_edges))

    def test_export_event_fixture_events_only(self) -> None:
        source_nodes, source_edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_export_fixture_") as td:
            out_dir = Path(td) / "valid_minimal_events"

            export_event_fixture(
                FIXTURE_DIR,
                out_dir,
                ts=1700000000,
                include_materialized_snapshot=False,
            )

            self.assertTrue((out_dir / "events.jsonl").is_file())
            self.assertFalse((out_dir / "nodes.json").exists())
            self.assertFalse((out_dir / "edges.json").exists())

            materialized = load_and_replay_events(out_dir)
            self.assertEqual(len(materialized.nodes), len(source_nodes))
            self.assertEqual(len(materialized.edges), len(source_edges))

