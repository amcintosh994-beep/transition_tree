from pathlib import Path
p = Path("tests/test_semantic_snapshot.py")
s = p.read_text(encoding="utf-8")
print("triple_single:", s.count("'''"))
print("triple_double:", s.count('"""'))
