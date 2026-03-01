# tests/test_determinism.py
from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from mttt.normalize_json import normalize_dir


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class TestDeterminism(unittest.TestCase):
    def test_normalize_is_idempotent_and_byte_stable(self):
        """
        Copy a known fixture directory to a temp dir.
        Run normalize twice.
        Assert byte-identical outputs across runs.
        """
        repo_root = Path(__file__).resolve().parents[1]
        fixture_dir = repo_root / "fixtures" / "valid_minimal"
        self.assertTrue(fixture_dir.exists(), f"Missing fixture dir: {fixture_dir}")

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            work = td_path / "work"
            shutil.copytree(fixture_dir, work)

            nodes = work / "nodes.json"
            edges = work / "edges.json"

            # First normalize
            normalize_dir(work)
            h1_nodes = sha256_file(nodes)
            h1_edges = sha256_file(edges)

            # Second normalize
            normalize_dir(work)
            h2_nodes = sha256_file(nodes)
            h2_edges = sha256_file(edges)

            self.assertEqual(h1_nodes, h2_nodes, "nodes.json changed after second normalize()")
            self.assertEqual(h1_edges, h2_edges, "edges.json changed after second normalize()")