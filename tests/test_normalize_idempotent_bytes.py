from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestNormalizeIdempotentBytes(unittest.TestCase):
    def test_normalize_twice_identical_bytes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        src_dir = repo_root / "fixtures" / "valid_minimal"
        self.assertTrue(src_dir.is_dir(), f"Missing fixtures dir: {src_dir}")

        with tempfile.TemporaryDirectory() as td:
            work_dir = Path(td) / "data"
            shutil.copytree(src_dir, work_dir)

            nodes = work_dir / "nodes.json"
            edges = work_dir / "edges.json"
            self.assertTrue(nodes.is_file(), f"Missing {nodes}")
            self.assertTrue(edges.is_file(), f"Missing {edges}")

            cmd = [
                sys.executable,
                "-m",
                "mttt.cli",
                "normalize",
                "--data-dir",
                str(work_dir),
            ]

            # Run 1
            p1 = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                p1.returncode,
                0,
                f"normalize run 1 failed\nSTDOUT:\n{p1.stdout}\nSTDERR:\n{p1.stderr}",
            )
            nodes_b1 = nodes.read_bytes()
            edges_b1 = edges.read_bytes()

            # Run 2
            p2 = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                p2.returncode,
                0,
                f"normalize run 2 failed\nSTDOUT:\n{p2.stdout}\nSTDERR:\n{p2.stderr}",
            )
            nodes_b2 = nodes.read_bytes()
            edges_b2 = edges.read_bytes()

            # Byte-identical idempotence
            self.assertEqual(nodes_b1, nodes_b2, "nodes.json changed on second normalize run")
            self.assertEqual(edges_b1, edges_b2, "edges.json changed on second normalize run")


if __name__ == "__main__":
    unittest.main()
