from __future__ import annotations

import unittest
from pathlib import Path

from mttt.state_provider import load_state


FIXTURE_DIR = Path("fixtures/valid_minimal")


class TestStateProvider(unittest.TestCase):
    def test_snapshot_provider_loads_fixture_state(self) -> None:
        loaded = load_state(FIXTURE_DIR, regime="snapshot")
        self.assertTrue(len(loaded.nodes) > 0)
        self.assertTrue(len(loaded.edges) > 0)
        self.assertEqual(loaded.provenance, "snapshot:nodes.json+edges.json")

    def test_events_provider_not_implemented_yet(self) -> None:
        with self.assertRaises(NotImplementedError):
            load_state(FIXTURE_DIR, regime="events")
