from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import json


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "mttt.cli", *args],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )


def test_cli_check_failure_exit_code(tmp_path) -> None:
    # Create minimal invalid fixture
    d = tmp_path / "invalid"
    d.mkdir()

    (d / "nodes.json").write_text("[]")
    (d / "edges.json").write_text("[]")

    r = run_cli("check", "--data-dir", str(d))
    assert r.returncode in (2, 3), (r.returncode, r.stdout, r.stderr)
