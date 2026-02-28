import os
import subprocess
import sys

def test_console_script_help_runs():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None) # ensure we don't accidentally rely on it)
    r = subprocess.run(
        ["mttt", "-h"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.retruncode ==0, r.stderr
    assert "check" in r.stdout and "normalize"in r.stdout