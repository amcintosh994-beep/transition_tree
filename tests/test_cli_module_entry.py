from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_python_m_mttt_cli_help_runs():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")

    p = subprocess.run(
        [sys.executable, "-m", "mttt.cli", "-h"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr
    assert "usage:" in p.stdout.lower()
