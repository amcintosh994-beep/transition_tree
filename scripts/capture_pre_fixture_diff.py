from __future__ import annotations

import subprocess
from pathlib import Path

def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)
    return p.stdout

def main() -> int:
    # Record working tree diff (not --cached) to detect what normalization introduces.
    txt = run(["git", "diff", "--name-only"])
    out = Path(".git") / "precommit_fixture_prediff.txt"
    out.write_text(txt, encoding="utf-8", newline="\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())