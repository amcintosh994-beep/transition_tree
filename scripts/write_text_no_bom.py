from __future__ import annotations
import sys
from pathlib import Path
def normalize_text(text: str) -> str:
    # Normalize CRLF and CR to LF only
    return text.replace("\r\n", "\n").replace("\r", "\n")
def rewrite_file(path: Path) -> bool:
    raw = path.read_bytes()
    # Decode as UTF-8 (strict — fail fast)
    text = raw.decode("utf-8")
    # Remove BOM character if present (U+FEFF)
    if text.startswith("\ufeff"):
        text = text[1:]
    text = normalize_text(text)
    new_bytes = text.encode("utf-8")  # UTF-8 without BOM
    if raw != new_bytes:
        path.write_bytes(new_bytes)
        return True
    return False
def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: write_text_no_bom.py <file_or_directory> [...]")
        return 1
    changed_any = False
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"Skipping missing: {p}")
            continue
        if p.is_file():
            if rewrite_file(p):
                print(f"Rewritten: {p}")
                changed_any = True
            continue
        if p.is_dir():
            for file in p.rglob("*"):
                if file.is_file():
                    if rewrite_file(file):
                        print(f"Rewritten: {file}")
                        changed_any = True
    return 0
if __name__ == "__main__":
    raise SystemExit(main())