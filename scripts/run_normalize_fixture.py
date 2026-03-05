from __future__ import annotations
import mttt
import mttt.io_atomic
print("MTTT_IMPORT:", mttt.__file__)
print("IO_ATOMIC_IMPORT:", mttt.io_atomic.__file__)

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    fixture = repo / 'fixtures' / 'valid_minimal'

    if not fixture.is_dir():
        print(f'Missing fixture dir: {fixture}', file=sys.stderr)
        return 2

    cmd = [sys.executable, '-m', 'mttt.cli', 'normalize', '--data-dir', str(fixture)]
    return subprocess.call(cmd, cwd=str(repo))


if __name__ == '__main__':
    raise SystemExit(main())
