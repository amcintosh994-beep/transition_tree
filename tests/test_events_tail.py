from __future__ import annotations

import json
import tempfile
import unittest
from collections import deque
from pathlib import Path

from mttt.events import append_set_state_event
from mttt.loader_json import load_nodes_edges_from_dir


FIXTURE_DIR = Path("fixtures/valid_minimal")


def _read_tail_events(events_path: Path, limit: int) -> list[dict]:
    tail: deque[dict] = deque(maxlen=limit)
    with events_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            tail.append(json.loads(line))
    return list(tail)


class TestEventsTail(unittest.TestCase):
    def test_tail_returns_last_n_events(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_events_tail_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)
            append_set_state_event(data_dir, nodes, edges, ts=1700000002)

            events_path = data_dir / "events.jsonl"
            tail = _read_tail_events(events_path, limit=2)

            self.assertEqual(len(tail), 2)
            self.assertEqual(tail[0]["ts"], 1700000001)
            self.assertEqual(tail[1]["ts"], 1700000002)

    def test_tail_handles_limit_larger_than_log(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_events_tail_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)

            events_path = data_dir / "events.jsonl"
            tail = _read_tail_events(events_path, limit=10)

            self.assertEqual(len(tail), 1)
            self.assertEqual(tail[0]["ts"], 1700000000)
            self.assertEqual(tail[0]["type"], "SET_STATE")
