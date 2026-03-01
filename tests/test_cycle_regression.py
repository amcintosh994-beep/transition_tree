from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
FIXTURE_DIR = Path("fixtures/valid_minimal")
SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_PATH = SNAPSHOT_DIR / "invalid_cycle_check.txt"
def _canon(text: str, work_dir: Path) -> str:
    """Canonicalize tool output so snapshots are stable across machines/paths."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "/")
    wd = str(work_dir).replace("\\", "/")
    text = text.replace(wd, "<WORKDIR>")
    text = re.sub(r"[A-Za-z]:/[^\n\r\t]+", "<PATH>", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    if not text.endswith("\n"):
        text += "\n"
    return text
def _dump_snapshot(payload: dict, work_dir: Path) -> str:
    """Deterministic JSON dump for the snapshot artifact."""
    txt = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    return _canon(txt + "\n", work_dir)
def _infer_src_dst_keys(edge_obj: dict, node_ids: set[str]) -> tuple[str, str]:
    """Infer the (src,dst) field names by locating two fields whose values are node IDs."""
    hits = [k for k, v in edge_obj.items() if isinstance(v, str) and v in node_ids]
    if len(hits) >= 2:
        hits = sorted(hits)
        return hits[0], hits[1]
    raise AssertionError(
        f"Could not infer src/dst keys from edge object keys={sorted(edge_obj.keys())}"
    )
def _make_cycle_in_edges_json(work_dir: Path) -> None:
    nodes_path = work_dir / "nodes.json"
    edges_path = work_dir / "edges.json"
    nodes = json.loads(nodes_path.read_text(encoding="utf-8"))
    edges = json.loads(edges_path.read_text(encoding="utf-8"))
    node_ids: set[str] = set()
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict) and isinstance(n.get("id"), str):
                node_ids.add(n["id"])
    elif isinstance(nodes, dict):
        for k in nodes.keys():
            if isinstance(k, str):
                node_ids.add(k)
    if not node_ids:
        raise AssertionError("Could not determine node IDs from nodes.json")
    if not isinstance(edges, list) or not edges:
        raise AssertionError("edges.json must be a non-empty list for this regression test")
    base = edges[0]
    if not isinstance(base, dict):
        raise AssertionError("edges.json first element is not an object")
    src_k, dst_k = _infer_src_dst_keys(base, node_ids)
    rev = dict(base)
    rev[src_k], rev[dst_k] = base[dst_k], base[src_k]
    if isinstance(rev.get("id"), str):
        rev["id"] = rev["id"] + "__rev"
    edges.append(rev)
    edges_path.write_text(
        json.dumps(edges, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
class TestCycleRegression(unittest.TestCase):
    def test_cycle_is_rejected_and_snapshotted(self) -> None:
        if not FIXTURE_DIR.is_dir():
            self.fail(f"Missing fixture directory: {FIXTURE_DIR}")
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mttt_cycle_") as td:
            work_dir = Path(td) / "cycle_fixture"
            shutil.copytree(FIXTURE_DIR, work_dir, dirs_exist_ok=True)
            _make_cycle_in_edges_json(work_dir)
            subprocess.check_call(
                [sys.executable, "-m", "mttt.cli", "normalize", "--data-dir", str(work_dir)],
                cwd=Path.cwd(),
            )
            proc = subprocess.run(
                [sys.executable, "-m", "mttt.cli", "check", "--data-dir", str(work_dir)],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            payload = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
            self.assertNotEqual(
                proc.returncode, 0, "Expected mttt.cli check to fail on a cycle, but it succeeded"
            )
            actual = _dump_snapshot(payload, work_dir)
            update = os.environ.get("UPDATE_SNAPSHOTS", "").strip().lower() in {"1", "true", "yes"}
            if update or not SNAPSHOT_PATH.exists():
                SNAPSHOT_PATH.write_text(actual, encoding="utf-8", newline="\n")
                self.assertTrue(SNAPSHOT_PATH.stat().st_size > 0)
                return
            expected = SNAPSHOT_PATH.read_text(encoding="utf-8")
            self.assertEqual(expected, actual)
if __name__ == "__main__":
    raise SystemExit(unittest.main())
