"""
SQL Query Runner
Runs all leakage detection queries against the SQLite database
and displays results in a readable format.
"""

import sqlite3
import os

DB_PATH = "data/db/leakage.db"

TITLES = [
    "Query 1: Daily MNF Summary per Zone",
    "Query 2: High MNF Risk Days",
    "Query 3: Pressure Drop Detection",
    "Query 4: Combined Alert - Confirmed Leakage Events"
]

def run_queries():
    conn = sqlite3.connect(DB_PATH)
    print("✅ Connected to database\n")

    with open("sql/queries.sql", "r") as f:
        sql = f.read()

    # Split queries by semicolon, remove comments and empty ones
    raw_queries = sql.split(";")
    queries = []
    for q in raw_queries:
        lines = [
            line for line in q.strip().splitlines()
            if not line.strip().startswith("--")
        ]
        cleaned = "\n".join(lines).strip()
        if cleaned:
            queries.append(cleaned)

    for i, query in enumerate(queries[:4]):
        print("=" * 65)
        print(f"🔍 {TITLES[i]}")
        print("=" * 65)

        try:
            cursor = conn.execute(query)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()

            # Print column headers
            print(" | ".join(f"{c:<20}" for c in cols))
            print("-" * 65)

            # Print rows
            for row in rows[:10]:
                print(" | ".join(f"{str(v):<20}" for v in row))

            print(f"\nTotal rows returned: {len(rows)}\n")

        except Exception as e:
            print(f"❌ Error in query {i+1}: {e}\n")

    conn.close()
    print("✅ All queries complete!")

if __name__ == "__main__":
    run_queries()