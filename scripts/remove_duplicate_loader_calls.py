from pathlib import Path
p = Path("tests/test_semantic_snapshot.py")
text = p.read_text(encoding="utf-8")
target = "nodes_obj, edges_obj = load_nodes_edges_from_dir(work_dir)"
count = 0
new_lines = []
for line in text.splitlines(True):
    if target in line:
        count += 1
        if count >= 2:
            continue
    new_lines.append(line)
p.write_text("".join(new_lines), encoding="utf-8", newline="\n")
print("Removed duplicate call sites:", max(0, count-1))
