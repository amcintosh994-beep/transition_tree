from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mttt.events import edge_to_dict, node_to_dict
from mttt.loader_json import load_nodes_edges_from_dir
from mttt.state_provider import load_state


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestStateProvider(unittest.TestCase):
    def test_snapshot_provider_loads_fixture_state(self) -> None:
        loaded = load_state(FIXTURE_DIR, regime="snapshot")
        self.assertTrue(len(loaded.nodes) > 0)
        self.assertTrue(len(loaded.edges) > 0)
        self.assertEqual(loaded.provenance, "snapshot:nodes.json+edges.json")

    def test_events_provider_replays_set_state(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        payload = {
            "nodes": [node_to_dict(n) for n in nodes],
            "edges": [edge_to_dict(e) for e in edges],
        }

        event = {
            "v": 1,
            "ts": 1700000000,
            "type": "SET_STATE",
            "payload": payload,
        }

        with tempfile.TemporaryDirectory(prefix="mttt_events_") as td:
            data_dir = Path(td)
            (data_dir / "events.jsonl").write_text(
                json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            loaded = load_state(data_dir, regime="events")
            self.assertEqual(len(loaded.nodes), len(nodes))
            self.assertEqual(len(loaded.edges), len(edges))
            self.assertEqual(loaded.provenance, "events:events.jsonl")

    def test_events_provider_rejects_unknown_event_type(self) -> None:
        event = {
            "v": 1,
            "ts": 1700000000,
            "type": "BOGUS",
            "payload": {},
        }

        with tempfile.TemporaryDirectory(prefix="mttt_events_") as td:
            data_dir = Path(td)
            (data_dir / "events.jsonl").write_text(
                json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaises(ValueError):
                load_state(data_dir, regime="events")
