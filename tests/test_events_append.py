from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mttt.events import append_set_state_event, load_and_replay_events
from mttt.loader_json import load_nodes_edges_from_dir


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestEventsAppend(unittest.TestCase):
    def test_append_set_state_creates_events_log_and_replays(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_append_") as td:
            data_dir = Path(td)

            out_path = append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            self.assertTrue(out_path.is_file())
            self.assertEqual(out_path.name, "events.jsonl")

            raw = out_path.read_text(encoding="utf-8")
            self.assertNotIn("\r", raw)
            self.assertTrue(raw.endswith("\n"))

            lines = raw.splitlines()
            self.assertEqual(len(lines), 1)

            obj = json.loads(lines[0])
            self.assertEqual(obj["type"], "SET_STATE")
            self.assertEqual(obj["v"], 1)
            self.assertEqual(obj["ts"], 1700000000)

            materialized = load_and_replay_events(data_dir)
            self.assertEqual(len(materialized.nodes), len(nodes))
            self.assertEqual(len(materialized.edges), len(edges))

    def test_append_set_state_appends_second_event(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_append_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)

            raw = (data_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("\r", raw)
            self.assertTrue(raw.endswith("\n"))

            lines = raw.splitlines()
            self.assertEqual(len(lines), 2)

            first = json.loads(lines[0])
            second = json.loads(lines[1])

            self.assertEqual(first["ts"], 1700000000)
            self.assertEqual(second["ts"], 1700000001)
