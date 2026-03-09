from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import (
    append_set_state_event,
    compact_events_in_dir,
    edge_to_dict,
    export_event_fixture,
    load_and_replay_events,
    materialize_events_to_dir,
    node_to_dict,
)
from mttt.loader_json import load_nodes_edges_from_dir


FIXTURE_DIR = Path("fixtures/valid_minimal")


def _canon_nodes(nodes):
    return [node_to_dict(n) for n in nodes]


def _canon_edges(edges):
    return [edge_to_dict(e) for e in edges]


class TestRoundTripEquivalence(unittest.TestCase):
    def test_snapshot_export_replay_materialize_reload_equivalent(self) -> None:
        src_nodes, src_edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        expected_nodes = _canon_nodes(src_nodes)
        expected_edges = _canon_edges(src_edges)

        with tempfile.TemporaryDirectory(prefix="mttt_roundtrip_") as td:
            out_dir = Path(td) / "valid_minimal_events"

            # snapshot -> export canonical event fixture
            export_event_fixture(
                FIXTURE_DIR,
                out_dir,
                ts=1700000000,
                include_materialized_snapshot=False,
            )

            # event replay must match original semantic state
            replayed = load_and_replay_events(out_dir)
            self.assertEqual(expected_nodes, _canon_nodes(replayed.nodes))
            self.assertEqual(expected_edges, _canon_edges(replayed.edges))

            # materialize canonical snapshot files from event authority
            materialize_events_to_dir(out_dir)

            # reload materialized snapshot and compare again
            loaded_nodes, loaded_edges = load_nodes_edges_from_dir(out_dir)
            self.assertEqual(expected_nodes, _canon_nodes(loaded_nodes))
            self.assertEqual(expected_edges, _canon_edges(loaded_edges))

    def test_append_then_compact_preserves_semantic_state(self) -> None:
        src_nodes, src_edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        expected_nodes = _canon_nodes(src_nodes)
        expected_edges = _canon_edges(src_edges)

        with tempfile.TemporaryDirectory(prefix="mttt_roundtrip_") as td:
            data_dir = Path(td)

            # create a non-trivial log with multiple SET_STATE events
            append_set_state_event(data_dir, src_nodes, src_edges, ts=1700000000)
            append_set_state_event(data_dir, src_nodes, src_edges, ts=1700000001)

            before = load_and_replay_events(data_dir)
            self.assertEqual(expected_nodes, _canon_nodes(before.nodes))
            self.assertEqual(expected_edges, _canon_edges(before.edges))

            # compact to a single canonical SET_STATE event
            compact_events_in_dir(data_dir, ts=1700000002)

            after = load_and_replay_events(data_dir)
            self.assertEqual(expected_nodes, _canon_nodes(after.nodes))
            self.assertEqual(expected_edges, _canon_edges(after.edges))
