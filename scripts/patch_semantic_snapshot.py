from __future__ import annotations
from pathlib import Path
import re
PATH = Path("tests/test_semantic_snapshot.py")
def main() -> int:
    s = PATH.read_text(encoding="utf-8")
    lines = s.splitlines(True)  # keep newlines
    out: list[str] = []
    i = 0
    # Helper: find first index of a line matching regex
    def find_idx(pattern: str) -> int | None:
        rx = re.compile(pattern)
        for j, ln in enumerate(lines):
            if rx.search(ln):
                return j
        return None
    # 1) Remove orphaned try/except block that references loader (if present)
    while True:
        start = None
        end = None
        # Find a "try:" line
        for j in range(i, len(lines)):
            if re.match(r"^\s*try:\s*$", lines[j]):
                # Only treat it as the orphan block if loader import appears soon after
                window = "".join(lines[j : min(j + 12, len(lines))])
                if "load_nodes_edges_from_dir" in window or "load_nodes_edges_From_dir" in window:
                    start = j
                    break
        if start is None:
            break
        # Find matching except block end (consume through the blank line after except-body if possible)
        for k in range(start + 1, len(lines)):
            if re.match(r"^\s*except\s+Exception\s*:\s*$", lines[k]):
                # consume except header + following indented body lines
                m = k + 1
                while m < len(lines) and (lines[m].startswith(" " * 4) or lines[m].startswith("\t") or lines[m].strip() == ""):
                    # stop once we hit an unindented non-blank line after a blank
                    if lines[m].strip() == "":
                        # peek next
                        if m + 1 < len(lines) and re.match(r"^\S", lines[m + 1]):
                            m += 1
                            break
                    m += 1
                end = m
                break
        if end is None:
            break
        # Drop that block
        del lines[start:end]
    # Refresh working copy after deletions
    # (We now do a second pass: remove *duplicate* ui_state assignment before the canonical loader block)
    marker_idx = find_idx(r"^\s*#\s*Load normalized nodes/edges from the working directory, then compute UI state\.\s*$")
    if marker_idx is not None:
        for j in range(0, marker_idx):
            if re.match(r"^\s*ui_state\s*=\s*compute_ui_state\(", lines[j]):
                del lines[j]
                break
    # 3) Fix UPDATE_SNAPSHOTS block overindent: lines that start with 12+ spaces should be 8 in that region
    # Heuristic: after "actual = _dump_canonical(...)" unindent any lines that start with 12 spaces to 8
    for j, ln in enumerate(lines):
        if re.match(r"^\s*actual\s*=\s*_dump_canonical\(", ln):
            # walk forward until end of method (dedent back to <=8 or class-level)
            k = j + 1
            while k < len(lines):
                if re.match(r"^\S", lines[k]):  # class/module level
                    break
                # If line has 12 leading spaces, drop 4
                if lines[k].startswith(" " * 12):
                    lines[k] = lines[k][4:]
                k += 1
            break
    PATH.write_text("".join(lines), encoding="utf-8", newline="\n")
    print(f"Patched: {PATH}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())