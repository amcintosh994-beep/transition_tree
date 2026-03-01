from __future__ import annotations
from pathlib import Path
p = Path("tests/test_semantic_snapshot.py")
lines = p.read_text(encoding="utf-8").splitlines(True)  # keep newlines
needle = "actual = _dump_canonical(snapshot_obj)"
inserted = False
out = []
for line in lines:
    if (not inserted) and (needle in line):
        # Determine indent from the 'actual =' line (should be 8 spaces inside the test method)
        indent = line[: len(line) - len(line.lstrip(" "))]
        block = [
            indent + "# Build semantic snapshot object (deterministic, JSON-serializable)\n",
            indent + "snapshot_obj = {\n",
            indent + "    \"fixture\": \"valid_minimal\",\n",
            indent + "    \"nodes\": nodes,\n",
            indent + "    \"edges\": edges,\n",
            indent + "    \"ui_state\": ui_state,\n",
            indent + "}\n",
            "\n",
        ]
        out.extend(block)
        inserted = True
    out.append(line)
if not inserted:
    raise SystemExit(f"ERROR: Could not find line containing: {needle}")
p.write_text("".join(out), encoding="utf-8", newline="\n")
print("Inserted snapshot_obj block before:", needle)
