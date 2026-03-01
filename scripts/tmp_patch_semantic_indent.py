from pathlib import Path
p = Path("tests/test_semantic_snapshot.py")
lines = p.read_text(encoding="utf-8").splitlines(True)  # keep newlines
out = []
for idx, line in enumerate(lines, start=1):
    # (A) Lines 85–86: dedent 12 -> 8 spaces
    if idx in (85, 86) and line.startswith("            "):  # 12 spaces
        line = line[4:]  # -> 8 spaces
    # (B) Line 93: indent actual=... into the method (0 -> 8 spaces)
    if idx == 93 and line.lstrip().startswith("actual = "):
        line = "        " + line.lstrip()
    # (C) Lines 97–100: indent under the "if update..." block (8 -> 12 spaces)
    if 97 <= idx <= 100 and line.startswith("        "):  # 8 spaces
        # only add 4 spaces if it isn't already 12+
        if not line.startswith("            "):
            line = "    " + line
    out.append(line)
p.write_text("".join(out), encoding="utf-8", newline="\n")
print("Patched:", p)
