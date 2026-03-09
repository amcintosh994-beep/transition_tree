from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import (
    append_set_state_event,
    load_and_replay_events,
)


class TestReplayDiagnostics(unittest.TestCase):

    def test_missing_events_log(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mttt_diag_") as td:
            data_dir = Path(td)

            with self.assertRaises(FileNotFoundError):
                load_and_replay_events(data_dir)

    def test_empty_events_log(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mttt_diag_") as td:
            data_dir = Path(td)
            events_path = data_dir / "events.jsonl"

            events_path.write_text("", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                load_and_replay_events(data_dir)

            self.assertIn("empty", str(ctx.exception))

    def test_until_ts_filters_out_all_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mttt_diag_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, [], [], ts=100)

            with self.assertRaises(ValueError) as ctx:
                load_and_replay_events(data_dir, until_ts=50)

            self.assertIn("No events satisfy ts <=", str(ctx.exception))

    def test_no_set_state_event(self) -> None:
        """
        Construct a synthetic log with events but no SET_STATE.
        """
        with tempfile.TemporaryDirectory(prefix="mttt_diag_") as td:
            data_dir = Path(td)
            events_path = data_dir / "events.jsonl"

            events_path.write_text(
                '{"ts": 1, "type": "NOOP", "v": 1, "payload": {}}\n',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as ctx:
                load_and_replay_events(data_dir)

            self.assertIn("no SET_STATE", str(ctx.exception))
