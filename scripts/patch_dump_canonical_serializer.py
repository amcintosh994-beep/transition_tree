from __future__ import annotations
from pathlib import Path
import sys
TARGET = Path("tests/test_semantic_snapshot.py")
REPLACEMENT = """def _dump_canonical(obj):
    \"\"\"Deterministic JSON serialization for snapshot testing.
    Converts common non-JSON types (dataclasses, Enums, Paths, sets, simple objects)
    into stable, JSON-serializable structures.
    \"\"\"
    import dataclasses
    import enum
    from pathlib import Path
    def _default(o):
        # dataclasses -> dict
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        # Enums -> value (or name if value not JSONable)
        if isinstance(o, enum.Enum):
            v = o.value
            if isinstance(v, (str, int, float, bool)) or v is None:
                return v
            return o.name
        # Paths -> string
        if isinstance(o, Path):
            return str(o)
        # sets -> sorted list (deterministic)
        if isinstance(o, set):
            return sorted(o)
        # tuples -> list
        if isinstance(o, tuple):
            return list(o)
        # generic objects -> __dict__ if available
        if hasattr(o, "__dict__"):
            return o.__dict__
        raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
    return json.dumps(
        obj,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        default=_default,
    ) + "\\n"
"""
def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: Missing {TARGET}")
        return 2
    lines = TARGET.read_text(encoding="utf-8").splitlines(True)  # keep newlines
    # Find start of function at top-level or indented (we'll still replace that block).
    start = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("def _dump_canonical"):
            start = i
            break
    if start is None:
        print("ERROR: Could not find a line starting with 'def _dump_canonical'.")
        return 3
    # Determine indentation of the def line (count leading spaces/tabs)
    def_line = lines[start]
    indent_prefix = def_line[: len(def_line) - len(def_line.lstrip())]
    # Find end: next line that is NOT blank and has indentation <= indent_prefix AND startswith def/class
    end = len(lines)
    for j in range(start + 1, len(lines)):
        raw = lines[j]
        if raw.strip() == "":
            continue
        # indentation of this line
        this_prefix = raw[: len(raw) - len(raw.lstrip())]
        if len(this_prefix) <= len(indent_prefix) and raw.lstrip().startswith(("def ", "class ")):
            end = j
            break
    # Build replacement with same indentation as original def (usually none)
    repl_lines = []
    for k, rline in enumerate(REPLACEMENT.splitlines(True)):
        if k == 0:
            repl_lines.append(indent_prefix + rline.rstrip("\n") + "\n")
        else:
            # preserve internal indentation in REPLACEMENT, but shift by indent_prefix
            repl_lines.append(indent_prefix + rline.rstrip("\n") + "\n")
    new_lines = lines[:start] + repl_lines + lines[end:]
    TARGET.write_text("".join(new_lines), encoding="utf-8", newline="\n")
    print(f"Patched _dump_canonical block in: {TARGET} (replaced lines {start+1}..{end})")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
