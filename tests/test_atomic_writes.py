from __future__ import annotations

import json
from pathlib import Path

from mttt.io_atomic import atomic_write_json


def test_atomic_write_json_is_valid_and_no_tmp_leftovers(tmp_path: Path) -> None:
    out = tmp_path / "state.json"
    payload = {"b": 2, "a": 1}

    atomic_write_json(out, payload)

    # JSON parseable
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == payload

    # LF + trailing newline invariant (drift resistance)
    raw = out.read_text(encoding="utf-8")
    assert "\r" not in raw
    assert raw.endswith("\n")

    # No leftover tmp files
    leftovers = list(tmp_path.glob(f".{out.name}.tmp.*"))
    assert leftovers == []
