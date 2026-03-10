from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from mttt.loader_json import load_nodes_edges_from_dir
from mttt.events import append_set_state_event


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestCliJsonDiagnostics(unittest.TestCase):
    def test_events_head_json_is_valid(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_cli_json_") as td:
            data_dir = Path(td)
            append_set_state_event(data_dir, nodes, edges, ts=1700000000)

            proc = subprocess.run(
                [
                    "python",
                    "-m",
                    "mttt.cli",
                    "events-head",
                    "--data-dir",
                    str(data_dir),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            obj = json.loads(proc.stdout)
            self.assertEqual(obj["events_jsonl"], "present")
            self.assertEqual(obj["events"], 1)
            self.assertEqual(obj["first_event_ts"], 1700000000)
            self.assertEqual(obj["last_event_ts"], 1700000000)

    def test_events_tail_json_is_valid(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_cli_json_") as td:
            data_dir = Path(td)
            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)

            proc = subprocess.run(
                [
                    "python",
                    "-m",
                    "mttt.cli",
                    "events-tail",
                    "--data-dir",
                    str(data_dir),
                    "--limit",
                    "2",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            obj = json.loads(proc.stdout)
            self.assertEqual(obj["events_jsonl"], "present")
            self.assertEqual(obj["showing"], 2)
            self.assertEqual(len(obj["events"]), 2)

            first = obj["events"][0]
            second = obj["events"][1]

            self.assertEqual(first["ts"], 1700000000)
            self.assertEqual(first["type"], "SET_STATE")
            self.assertEqual(first["v"], 1)
            self.assertEqual(first["nodes"], len(nodes))
            self.assertEqual(first["edges"], len(edges))

            self.assertEqual(second["ts"], 1700000001)
            self.assertEqual(second["type"], "SET_STATE")
            self.assertEqual(second["v"], 1)
            self.assertEqual(second["nodes"], len(nodes))
            self.assertEqual(second["edges"], len(edges))
