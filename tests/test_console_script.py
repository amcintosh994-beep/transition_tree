import os
import subprocess
import sys
from pathlib import Path

def test_console_script_mttt_help_runs():
    # We expect this to be run after editable install in CI,
    # but locally it's also useful once `pip install -e .`.
    r = subprocess.run(
        ["mttt", "-h"],
        capture_output=True,
        text=True,
        shell=False,
    )
    assert r.returncode == 0, r.stderr
    assert "check" in r.stdout
    assert "normalize" in r.stdout