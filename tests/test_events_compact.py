from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mttt.events import append_set_state_event, compact_events_in_dir, load_and_replay_events
from mttt.loader_json import load_nodes_edges_from_dir


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestEventsCompact(unittest.TestCase):
    def test_compact_events_rewrites_log_to_single_set_state(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_compact_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)

            raw_before = (data_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(len(raw_before.splitlines()), 2)

            out_path = compact_events_in_dir(data_dir, ts=1700000002)
            self.assertTrue(out_path.is_file())

            raw_after = out_path.read_text(encoding="utf-8")
            self.assertNotIn("\r", raw_after)
            self.assertTrue(raw_after.endswith("\n"))

            lines = raw_after.splitlines()
            self.assertEqual(len(lines), 1)

            obj = json.loads(lines[0])
            self.assertEqual(obj["type"], "SET_STATE")
            self.assertEqual(obj["v"], 1)
            self.assertEqual(obj["ts"], 1700000002)

    def test_compacted_log_replays_successfully(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_compact_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)
            compact_events_in_dir(data_dir, ts=1700000002)

            materialized = load_and_replay_events(data_dir)
            self.assertEqual(len(materialized.nodes), len(nodes))
            self.assertEqual(len(materialized.edges), len(edges))

