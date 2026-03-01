from __future__ import annotations
from pathlib import Path
p = Path("tests/test_semantic_snapshot.py")
lines = p.read_text(encoding="utf-8").splitlines(True)  # keep newlines
out = []
skipping = False
for line in lines:
    # Start skipping the erroneous "late import" semantic block.
    if "Compute semantic" in line:
        skipping = True
        continue
    if skipping:
        # End skip right before the assertion / snapshot write section resumes.
        if "actual = _dump_canonical(snapshot_obj)" in line:
            skipping = False
            out.append(line)
        # Otherwise drop everything in this block (includes the late import and duplicate ui_state).
        continue
    # Also drop the specific late import line if it exists outside the block.
    if "from mttt.pipeline import compute_ui_state" in line and "import late" in line:
        continue
    out.append(line)
p.write_text("".join(out), encoding="utf-8", newline="\n")
print("Patched:", p)
