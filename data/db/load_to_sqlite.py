"""
SQLite Database Loader
Loads the synthetic water network CSV data into a SQLite database
creating a proper database table for SQL querying and dbt transformations.
"""

import pandas as pd
import sqlite3
import os

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH   = os.path.join(BASE_DIR, "synthetic", "water_network_data.csv")
DB_PATH    = os.path.join(BASE_DIR, "db", "leakage.db")


def create_connection(db_path: str) -> sqlite3.Connection:
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    print(f"✅ Connected to database: {db_path}")
    return conn


def load_csv_to_db(conn: sqlite3.Connection, csv_path: str) -> None:
    """Load CSV data into SQLite as a table called raw_water_data."""
    print(f"\n📂 Reading CSV from: {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["date"])

    print(f"   Rows loaded: {len(df):,}")
    print(f"   Columns: {list(df.columns)}")

    # Write to SQLite — replace table if it already exists
    df.to_sql(
        name="raw_water_data",
        con=conn,
        if_exists="replace",
        index=False
    )
    print(f"\n✅ Data written to table: raw_water_data")


def verify_data(conn: sqlite3.Connection) -> None:
    """Run a quick verification query to confirm data loaded correctly."""
    print("\n🔍 Verifying data in database...")

    # Total row count
    cursor = conn.execute("SELECT COUNT(*) FROM raw_water_data")
    count = cursor.fetchone()[0]
    print(f"   Total rows in database: {count:,}")

    # Show distinct zones
    cursor = conn.execute(
        "SELECT zone_id, zone_name, COUNT(*) as days "
        "FROM raw_water_data "
        "GROUP BY zone_id, zone_name "
        "ORDER BY zone_id"
    )
    print(f"\n📊 Zones in database:")
    print(f"   {'Zone ID':<10} {'Zone Name':<15} {'Days'}")
    print(f"   {'-'*35}")
    for row in cursor.fetchall():
        print(f"   {row[0]:<10} {row[1]:<15} {row[2]}")

    # Show sample of anomaly days
    cursor = conn.execute(
        "SELECT date, zone_id, zone_name, mnf_ls, pressure_m, acoustic_alert "
        "FROM raw_water_data "
        "WHERE acoustic_alert = 1 "
        "ORDER BY date "
        "LIMIT 5"
    )
    print(f"\n🚨 Sample anomaly days (acoustic_alert = 1):")
    print(f"   {'Date':<12} {'Zone':<8} {'Name':<12} {'MNF':>6} {'Pressure':>10} {'Acoustic':>9}")
    print(f"   {'-'*60}")
    for row in cursor.fetchall():
        print(f"   {str(row[0]):<12} {row[1]:<8} {row[2]:<12} {row[3]:>6} {row[4]:>10} {row[5]:>9}")


def main():
    print("🌊 Loading water network data into SQLite...\n")

    # Verify CSV exists
    if not os.path.exists(CSV_PATH):
        print(f"❌ CSV file not found at: {CSV_PATH}")
        print("   Please run generate_data.py first!")
        return

    conn  = create_connection(DB_PATH)
    load_csv_to_db(conn, CSV_PATH)
    verify_data(conn)
    conn.close()

    print(f"\n🎉 Database ready at: {DB_PATH}")
    print("   You can now run SQL queries against this database!")


if __name__ == "__main__":
    main()