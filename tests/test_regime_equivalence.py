from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mttt.events import export_event_fixture
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


def _semantic_view(data_dir: Path, regime: str):
    loaded = load_state(data_dir, regime=regime)
    ui = compute_ui_state(loaded.nodes, loaded.edges, preferred_domain=None)

    return {
        "invariants": _canon_invariant_errors(ui.get("invariants")),
        "cnl_issues": _canon_cnl_issues(ui.get("cnl_issues")),
        "resume_pick": _canon_resume_pick(ui.get("resume_pick")),
    }


class TestRegimeEquivalence(unittest.TestCase):
    def test_snapshot_and_events_regimes_are_semantically_equivalent(self) -> None:
        snapshot_semantics = _semantic_view(FIXTURE_DIR, regime="snapshot")

        with tempfile.TemporaryDirectory(prefix="mttt_regime_equiv_") as td:
            out_dir = Path(td) / "valid_minimal_events"

            export_event_fixture(
                FIXTURE_DIR,
                out_dir,
                ts=1700000000,
                include_materialized_snapshot=True,
            )

            events_semantics = _semantic_view(out_dir, regime="events")
            snapshot_semantics_from_export = _semantic_view(out_dir, regime="snapshot")

            self.assertEqual(snapshot_semantics, events_semantics)
            self.assertEqual(snapshot_semantics, snapshot_semantics_from_export)

