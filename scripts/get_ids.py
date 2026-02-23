import sqlite3

DB = "tree.db"

TARGETS = [
    (1, "Presentation baseline for everyday errands"),
    (2, "Crisis plan and decompression routine (ongoing)"),
    (3, "Access pathway: prescriber, labs, pharmacy"),
    (4, "Practice routine design (ongoing)"),
    (5, "Name change pathway"),
    (7, "Low-effort hair routine (ongoing)"),
    (8, "I have decided workplace disclosure and risk assessment"),
    (9, "I have decided to sequence transition steps over the next 8 weeks based on sustainability, risk, and budget constraints"),
]

def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    print("domain\tid\ttype\ttext")
    for domain_id, text in TARGETS:
        rows = conn.execute(
            "SELECT domain_id, id, type, text FROM nodes WHERE domain_id=? AND text=?",
            (domain_id, text),
        ).fetchall()

        if not rows:
            print(f"{domain_id}\t<NOT FOUND>\t-\t{text}")
            continue

        for r in rows:
            print(f"{r['domain_id']}\t{r['id']}\t{r['type']}\t{r['text']}")

    conn.close()

if __name__ == "__main__":
    main()
