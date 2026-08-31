import csv

import load_data


def test_row_counts_match_csv(conn):
    with open(load_data.CSV_PATH, newline="") as f:
        n_csv_rows = sum(1 for _ in csv.DictReader(f))

    n_samples = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    n_cell_counts = conn.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0]

    assert n_samples == n_csv_rows
    assert n_cell_counts == n_csv_rows * len(load_data.POPULATIONS)


def test_every_sample_has_a_real_subject(conn):
    n_orphans = conn.execute(
        "SELECT COUNT(*) FROM samples s "
        "LEFT JOIN subjects su ON s.subject_id = su.subject_id "
        "WHERE su.subject_id IS NULL"
    ).fetchone()[0]
    assert n_orphans == 0


def test_every_cell_count_row_has_a_real_sample(conn):
    n_orphans = conn.execute(
        "SELECT COUNT(*) FROM cell_counts cc "
        "LEFT JOIN samples s ON cc.sample_id = s.sample_id "
        "WHERE s.sample_id IS NULL"
    ).fetchone()[0]
    assert n_orphans == 0


def test_sample_ids_are_unique(conn):
    n_samples = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    n_distinct = conn.execute("SELECT COUNT(DISTINCT sample_id) FROM samples").fetchone()[0]
    assert n_samples == n_distinct
