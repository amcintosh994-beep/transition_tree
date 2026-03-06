from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically write UTF-8 text with LF endings and a trailing newline.

    Strategy: write to a temp file in the same directory, fsync, then os.replace().
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"

    tmp_dir = str(path.parent)
    prefix = f".{path.name}.tmp."
    fd, tmp_name = tempfile.mkstemp(prefix=prefix, dir=tmp_dir, text=True)
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


def atomic_write_json(path: Path, obj: Any) -> None:
    """Atomically write canonical JSON (sorted keys, stable separators, LF, newline)."""
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    atomic_write_text(Path(path), text)
