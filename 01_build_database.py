"""
01_build_database.py
Loads the raw CSVs into a proper SQLite database with sensible types,
so all downstream analysis can be done in SQL (as ZS's technical rounds
expect) rather than just in pandas.
"""
import sqlite3
import pandas as pd

DB_PATH = "ipl.db"

def main():
    matches = pd.read_csv("data/matches.csv")
    deliveries = pd.read_csv("data/deliveries.csv")

    # Basic cleaning
    matches["date"] = pd.to_datetime(matches["date"])
    matches["winner"] = matches["winner"].fillna("No Result")

    conn = sqlite3.connect(DB_PATH)
    matches.to_sql("matches", conn, if_exists="replace", index=False)
    deliveries.to_sql("deliveries", conn, if_exists="replace", index=False)

    # Indexes -- this is the kind of thing an interviewer likes to hear you
    # mention even if not asked: query performance matters, not just correctness.
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_match ON deliveries(match_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_batsman ON deliveries(batsman)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_bowler ON deliveries(bowler)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season)")
    conn.commit()

    print(f"Loaded {len(matches)} matches and {len(deliveries)} deliveries into {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    main()
