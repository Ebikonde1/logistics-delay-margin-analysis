"""Run every named query in sql/analysis.sql against logistics.db,
export each result to outputs/<name>.csv (Tableau-ready), and print a
formatted summary to the console."""

import csv
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

sql_text = (ROOT / "sql" / "analysis.sql").read_text(encoding="utf-8")

# Split on "-- name: <slug>" markers; each block runs up to the next marker.
blocks = re.split(r"--\s*name:\s*(\w+)", sql_text)[1:]
queries = list(zip(blocks[0::2], blocks[1::2]))

con = sqlite3.connect(ROOT / "logistics.db")

for name, body in queries:
    stmt = body.split(";")[0] + ";"
    cur = con.execute(stmt)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()

    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)

    print(f"\n=== {name} ({len(rows)} rows -> outputs/{name}.csv) " + "=" * 20)
    widths = [max(len(str(c)), max((len(str(r[i])) for r in rows[:15]), default=0))
              for i, c in enumerate(cols)]
    print("  " + " | ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    for r in rows[:15]:
        print("  " + " | ".join(str(v).ljust(w) for v, w in zip(r, widths)))
    if len(rows) > 15:
        print(f"  ... {len(rows) - 15} more rows in CSV")

con.close()
print(f"\nAll extracts written to {OUT}")
