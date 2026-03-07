from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ALLOWED_PREFIX = "fixtures/valid_minimal/"
PREDIFF_PATH = Path(".git") / "precommit_fixture_prediff.txt"

def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr)
        raise SystemExit(p.returncode)
    return p.stdout

def main() -> int:
    if not PREDIFF_PATH.exists():
        sys.stderr.write(f"Missing prediff marker: {PREDIFF_PATH}\n")
        sys.stderr.write("Hook ordering error: capture_pre_fixture_diff.py must run before normalization.\n")
        return 2

    before = {line.strip().replace("\\\\", "/") for line in PREDIFF_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}
    after_txt = run(["git", "diff", "--name-only"])
    after = {line.strip().replace("\\\\", "/") for line in after_txt.splitlines() if line.strip()}

    introduced = sorted(after - before)

    offenders = [p for p in introduced if not p.startswith(ALLOWED_PREFIX)]
    if offenders:
        sys.stderr.write("Fixture normalization introduced changes outside allowed directory:\n")
        for p in offenders:
            sys.stderr.write(f"  {p}\n")
        return 2

    return 0

if __name__ == "__main__":
    raise SystemExit(main())