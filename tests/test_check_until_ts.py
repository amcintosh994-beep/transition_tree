from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import append_set_state_event
from mttt.loader_json import load_nodes_edges_from_dir
from mttt.pipeline import compute_ui_state
from mttt.state_provider import load_state


FIXTURE_DIR = Path("fixtures/valid_minimal")


def _canon_resume_pick(rp):
    if rp is None:
        return None
    return {
        "node_id": getattr(rp, "node_id", None),
        "reason": getattr(rp, "reason", None),
    }


def _canon_invariant_errors(inv):
    if inv is None:
        return None

    errors = []
    for e in getattr(inv, "errors", []):
        errors.append(
            {
                "code": getattr(e, "code", None),
                "severity": getattr(e, "severity", None),
                "node_id": getattr(e, "node_id", None),
                "edge": getattr(e, "edge", None),
                "message": getattr(e, "message", None),
            }
        )

    return {
        "ok": getattr(inv, "ok", None),
        "errors": errors,
    }


def _canon_cnl_issues(issues):
    out = []
    for i in issues or []:
        out.append(
            {
                "node_id": getattr(i, "node_id", None),
                "code": getattr(i, "code", None),
                "message": getattr(i, "message", None),
            }
        )
    return out


def _semantic_view(data_dir: Path, regime: str, until_ts: int | None = None):
    loaded = load_state(data_dir, regime=regime, until_ts=until_ts)
    ui = compute_ui_state(loaded.nodes, loaded.edges, preferred_domain=None)

    return {
        "invariants": _canon_invariant_errors(ui.get("invariants")),
        "cnl_issues": _canon_cnl_issues(ui.get("cnl_issues")),
        "resume_pick": _canon_resume_pick(ui.get("resume_pick")),
    }


class TestCheckUntilTs(unittest.TestCase):
    def test_historical_check_semantics_match_first_event_state(self) -> None:
        nodes, edges = load_nodes_edges_from_dir(FIXTURE_DIR)

        with tempfile.TemporaryDirectory(prefix="mttt_check_until_ts_") as td:
            data_dir = Path(td)

            append_set_state_event(data_dir, nodes, edges, ts=1700000000)
            append_set_state_event(data_dir, nodes, edges, ts=1700000001)

            full_semantics = _semantic_view(data_dir, regime="events")
            historical_semantics = _semantic_view(
                data_dir,
                regime="events",
                until_ts=1700000000,
            )

            self.assertEqual(full_semantics, historical_semantics)
