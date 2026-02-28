from __future__ import annotations

import pathlib
import subprocess

# Reject UTF-8 BOM in tracked text-like files where BOM is never acceptable.
EXTS = {".py", ".yml", ".yaml", ".toml", ".md", ".json"}

def main() -> int:
    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    bad: list[str] = []

    for f in files:
        p = pathlib.Path(f)
        if p.suffix.lower() not in EXTS:
            continue
        if not p.is_file():
            continue
        b = p.read_bytes()
        if b.startswith(b"\xef\xbb\xbf"):
            bad.append(f)

    if bad:
        print("UTF-8 BOM detected in:")
        for x in bad:
            print(f"  {x}")
        return 1

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
