from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import append_set_state_event, replay_summary
from mttt.loader_json import load_nodes_edges_from_dir


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestReplaySummary(unittest.TestCase):
    def test_replay_summary_reports_event_log_and_end_state(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_replay_summary_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)

            summary = replay_summary(data_dir)

            self.assertEqual(summary["events_jsonl"], "present")
            self.assertEqual(summary["events"], 2)
            self.assertEqual(summary["last_event_ts"], 1700000001)
            self.assertEqual(summary["state_nodes"], len(nodes))
            self.assertEqual(summary["state_edges"], len(edges))
            self.assertEqual(summary["regime"], "events")


def test_replay_summary_until_ts_filters_visible_history(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_replay_summary_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)

            summary = replay_summary(data_dir, until_ts=1700000000)

            self.assertEqual(summary["events_jsonl"], "present")
            self.assertEqual(summary["events"], 1)
            self.assertEqual(summary["last_event_ts"], 1700000000)
            self.assertEqual(summary["state_nodes"], len(nodes))
            self.assertEqual(summary["state_edges"], len(edges))
            self.assertEqual(summary["regime"], "events")
            self.assertEqual(summary["until_ts"], 1700000000)
