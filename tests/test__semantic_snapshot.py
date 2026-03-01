from __future__ import annotations

import dataclasses
import enum
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path("fixtures/valid_minimal")
SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_PATH = SNAPSHOT_DIR / "valid_minimal.snapshot.json"


def _to_jsonable(x: Any) -> Any:
    """Best-effort deterministic conversion for dataclasses/enums/sets/paths."""
    if dataclasses.is_dataclass(x):
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(x).items()}

    if isinstance(x, enum.Enum):
        return x.name

    if isinstance(x, Path):
        return str(x)

    if isinstance(x, (str, int, float, bool)) or x is None:
        return x

    if isinstance(x, dict):
        # Sort keys at serialization time; keep structure jsonable here.
        return {str(k): _to_jsonable(v) for k, v in x.items()}

    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]

    if isinstance(x, set):
        # Deterministic order
        return sorted((_to_jsonable(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True))

    # Fallback: stable repr (last resort, but deterministic given stable ordering upstream)
    return repr(x)


def _dump_canonical(obj: Any) -> str:
    """Canonical JSON text: stable keys, stable indentation, LF-only."""
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).replace("\r\n", "\n").replace("\r", "\n") + "\n"


class TestSemanticSnapshot(unittest.TestCase):
    def test_valid_minimal_semantic_snapshot(self) -> None:
        if not FIXTURE_DIR.is_dir():
            self.fail(f"Missing fixture directory: {FIXTURE_DIR}")

        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="mttt_snapshot_") as td:
            td_path = Path(td)
            work_dir = td_path / "valid_minimal"
            shutil.copytree(FIXTURE_DIR, work_dir)

            # 1) Normalize via CLI (ensures we snapshot the *same* behavior as your gates)
            subprocess.check_call(
                [sys.executable, "-m", "mttt.cli", "normalize", "--data-dir", str(work_dir)],
                cwd=Path.cwd(),
            )

            # 2) Load normalized nodes/edges (these are the canonical persisted artifacts)
            nodes_text = (work_dir / "nodes.json").read_text(encoding="utf-8")
            edges_text = (work_dir / "edges.json").read_text(encoding="utf-8")
            nodes = json.loads(nodes_text)
            edges = json.loads(edges_text)

            # 3) Compute semantic “end-state” (UI state / derived states, etc.)
            #    This is the part that makes the snapshot *semantic*, not just structural.
            from mttt.pipeline import compute_ui_state  # import late for clearer failures
            
            # Prefer your loader if available; otherwise fall back to parsed JSON.
            try:
                from mttt.loader_json import load_nodes_edges_from_dir
                
                nodes_obj, edges_obj = load_nodes_edges_From_dir(work_dir)
            except Exception:
                nodes_obj = nodes
                edges_obj = edges
            
            ui_state = compute_ui_state(nodes_obj, edges_obj)

        # Load normalized nodes/edges from the working directory, then compute UI state.
        from mttt.loader_json import load_nodes_edges_from_dir
        nodes_obj, edges_obj = load_nodes_edges_from_dir(work_dir)
        ui_state = compute_ui_state(nodes_obj, edges_obj)
            snapshot_obj = {
                "fixture": "fixtures/valid_minimal",
                "nodes_json": nodes,
                "edges_json": edges,
                "ui_state": _to_jsonable(ui_state),
            }

            actual = _dump_canonical(snapshot_obj)

            update = os.environ.get("UPDATE_SNAPSHOTS", "").strip().lower() in {"1", "true", "yes"}
            if update or not SNAPSHOT_PATH.exists():
                SNAPSHOT_PATH.write_text(actual, encoding="utf-8", newline="\n")
                # If updating, still assert existence + non-empty
                self.assertTrue(SNAPSHOT_PATH.stat().st_size > 0)
                return

            expected = SNAPSHOT_PATH.read_text(encoding="utf-8")
            self.assertEqual(expected, actual)
