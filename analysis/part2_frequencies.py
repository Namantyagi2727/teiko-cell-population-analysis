"""
Part 2: relative frequency of each cell population in each sample.

Reads cell_counts.db and writes output/part2_frequencies.csv with columns:
sample, total_count, population, count, percentage.
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cell_counts.db"
OUTPUT_PATH = ROOT / "output" / "part2_frequencies.csv"

QUERY = """
SELECT
    cc.sample_id AS sample,
    SUM(cc.count) OVER (PARTITION BY cc.sample_id) AS total_count,
    cc.population AS population,
    cc.count AS count,
    ROUND(
        100.0 * cc.count / SUM(cc.count) OVER (PARTITION BY cc.sample_id), 4
    ) AS percentage
FROM cell_counts cc
ORDER BY cc.sample_id, cc.population;
"""


def compute_frequencies(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(QUERY, conn)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = compute_frequencies(conn)
    finally:
        conn.close()

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT_PATH}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
