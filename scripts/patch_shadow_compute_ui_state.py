from pathlib import Path
import re
p = Path("tests/test_semantic_snapshot.py")
s = p.read_text(encoding="utf-8")
# Rename any local assignment to compute_ui_state (shadowing bug)
# Only matches at line start (after indentation), i.e. "    compute_ui_state = ..."
pattern = re.compile(r"(?m)^(\s*)compute_ui_state(\s*)=")
new_s, n = pattern.subn(r"\1compute_ui_state_fn\2=", s)
p.write_text(new_s, encoding="utf-8", newline="\n")
print("Patched:", p, "renamed assignments:", n)
