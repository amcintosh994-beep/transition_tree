from __future__ import annotations
from mttt.loader_json import load_nodes_edges_from_dir

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

from mttt.normalize_json import normalize_dir


from mttt.pipeline import compute_ui_state
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


def _dump_canonical(obj):
    """Deterministic JSON serialization for snapshot testing.
    Converts common non-JSON types (dataclasses, Enums, Paths, sets, simple objects)
    into stable, JSON-serializable structures.
    """
    import dataclasses
    import enum
    from pathlib import Path
    def _default(o):
        # dataclasses -> dict
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        # Enums -> value (or name if value not JSONable)
        if isinstance(o, enum.Enum):
            v = o.value
            if isinstance(v, (str, int, float, bool)) or v is None:
                return v
            return o.name
        # Paths -> string
        if isinstance(o, Path):
            return str(o)
        # sets -> sorted list (deterministic)
        if isinstance(o, set):
            return sorted(o)
        # tuples -> list
        if isinstance(o, tuple):
            return list(o)
        # generic objects -> __dict__ if available
        if hasattr(o, "__dict__"):
            return o.__dict__
        raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
    return json.dumps(
        obj,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        default=_default,
    ) + "\n"
class TestSemanticSnapshot(unittest.TestCase):
    def test_valid_minimal_semantic_snapshot(self) -> None:
        if not FIXTURE_DIR.is_dir():
            self.fail(f"Missing fixture directory: {FIXTURE_DIR}")

        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="mttt_snapshot_") as td:
            tmp_root = Path(td)
            work_dir = tmp_root / "valid_minimal"
            work_dir.mkdir(parents=True, exist_ok=True)
            
            # 1) copy fixture into working dir
            shutil.copytree(FIXTURE_DIR, work_dir, dirs_exist_ok=True)
            
            # 2) normalize *in place* (so we snapshot canonical semantics)
            normalize_dir(work_dir)
            
            # 3) now the loader should succeed
            nodes_obj, edges_obj = load_nodes_edges_from_dir(work_dir)
            ui_state = compute_ui_state(nodes_obj, edges_obj)

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

        # Build semantic snapshot object (deterministic, JSON-serializable)
        snapshot_obj = {
            "fixture": "valid_minimal",
            "nodes": nodes,
            "edges": edges,
            "ui_state": ui_state,
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

