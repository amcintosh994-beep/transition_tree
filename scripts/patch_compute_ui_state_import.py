from pathlib import Path
import re
p = Path("tests/test_semantic_snapshot.py")
lines = p.read_text(encoding="utf-8").splitlines(True)
out = []
inserted_import = False
# Detect whether module-level compute_ui_state import exists
has_module_import = any(
    re.match(r"^\s*from\s+mttt\.pipeline\s+import\s+compute_ui_state\s*$", ln)
    for ln in lines
)
for ln in lines:
    # Remove any *in-function* import of compute_ui_state (common source of UnboundLocalError)
    if re.match(r"^\s+from\s+mttt\.pipeline\s+import\s+compute_ui_state\s*$", ln):
        # only drop indented ones; keep module-level import if present
        continue
    out.append(ln)
# If no module-level import, insert it at top after existing imports
if not has_module_import:
    new_out = []
    inserted = False
    for ln in out:
        new_out.append(ln)
        # after the last import line near the top, insert our import once
        if not inserted and re.match(r"^\s*(import\s+\w+|from\s+\w+(\.\w+)*\s+import\s+.+)\s*$", ln):
            # keep scanning; we'll insert after the import block ends
            pass
    # find end of import block (first non-import, non-blank after seeing imports)
    final = []
    seen_import = False
    inserted = False
    for ln in out:
        if re.match(r"^\s*(import\s+\w+|from\s+\w+(\.\w+)*\s+import\s+.+)\s*$", ln):
            seen_import = True
            final.append(ln)
            continue
        if seen_import and not inserted and ln.strip() != "":
            final.append("from mttt.pipeline import compute_ui_state\n")
            inserted = True
        final.append(ln)
    out = final
p.write_text("".join(out), encoding="utf-8", newline="\n")
print("Patched:", p)
