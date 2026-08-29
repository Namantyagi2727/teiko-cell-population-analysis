"""
Initializes cell_counts.db (SQLite) and loads cell-count.csv into it.

Schema (3 tables, normalized):

  subjects(subject_id PK, project, condition, age, sex)
      One row per patient. Attributes here are constant across all of a
      subject's samples (verified against the source data).

  samples(sample_id PK, subject_id FK, treatment, response, sample_type,
          time_from_treatment_start)
      One row per biological sample. treatment/response are stored here
      (not on subjects) so the schema still holds if a future dataset has
      subjects receiving more than one treatment over time.

  cell_counts(sample_id FK, population, count)
      Long/tidy format: one row per (sample, population) pair instead of
      one column per population. Adding a new cell population later, or a
      dataset where not every sample has every population measured, needs
      no schema change -- just more rows.

Run directly: `python load_data.py`. No arguments. Recreates the DB file
from scratch every run so it always matches the current CSV.
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "cell_counts.db"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

SCHEMA = """
CREATE TABLE subjects (
    subject_id  TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    condition   TEXT NOT NULL,
    age         INTEGER,
    sex         TEXT
);

CREATE TABLE samples (
    sample_id                 TEXT PRIMARY KEY,
    subject_id                TEXT NOT NULL REFERENCES subjects(subject_id),
    treatment                 TEXT,
    response                  TEXT,
    sample_type               TEXT NOT NULL,
    time_from_treatment_start INTEGER
);

CREATE TABLE cell_counts (
    sample_id  TEXT NOT NULL REFERENCES samples(sample_id),
    population TEXT NOT NULL,
    count      INTEGER NOT NULL,
    PRIMARY KEY (sample_id, population)
);

CREATE INDEX idx_samples_subject ON samples(subject_id);
CREATE INDEX idx_cellcounts_sample ON cell_counts(sample_id);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def load_csv(conn: sqlite3.Connection, csv_path: Path) -> None:
    subjects_seen = set()
    subject_rows = []
    sample_rows = []
    cell_count_rows = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject_id = row["subject"]
            if subject_id not in subjects_seen:
                subjects_seen.add(subject_id)
                subject_rows.append(
                    (
                        subject_id,
                        row["project"],
                        row["condition"],
                        int(row["age"]) if row["age"] else None,
                        row["sex"],
                    )
                )

            sample_rows.append(
                (
                    row["sample"],
                    subject_id,
                    row["treatment"],
                    row["response"] if row["response"] else None,
                    row["sample_type"],
                    int(row["time_from_treatment_start"])
                    if row["time_from_treatment_start"] != ""
                    else None,
                )
            )

            for population in POPULATIONS:
                cell_count_rows.append((row["sample"], population, int(row[population])))

    conn.executemany(
        "INSERT INTO subjects (subject_id, project, condition, age, sex) "
        "VALUES (?, ?, ?, ?, ?)",
        subject_rows,
    )
    conn.executemany(
        "INSERT INTO samples "
        "(sample_id, subject_id, treatment, response, sample_type, time_from_treatment_start) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        sample_rows,
    )
    conn.executemany(
        "INSERT INTO cell_counts (sample_id, population, count) VALUES (?, ?, ?)",
        cell_count_rows,
    )
    conn.commit()


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_csv(conn, CSV_PATH)
    finally:
        conn.close()

    print(f"Loaded {CSV_PATH.name} into {DB_PATH.name}")


if __name__ == "__main__":
    main()
