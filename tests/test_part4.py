import pandas as pd

from analysis.part4_subset import AVG_B_CELL_QUERY, BASELINE_QUERY


def test_baseline_subject_breakdown_sums_to_total(conn):
    baseline = pd.read_sql_query(BASELINE_QUERY, conn)
    subjects = baseline.drop_duplicates(subset="subject_id")

    assert subjects["response"].value_counts().sum() == len(subjects)
    assert subjects["sex"].value_counts().sum() == len(subjects)


def test_baseline_samples_all_time_zero_pbmc_miraclib_melanoma(conn):
    baseline = pd.read_sql_query(BASELINE_QUERY, conn)
    # BASELINE_QUERY's own WHERE clause enforces this; re-running the same
    # filters independently here guards against the query being edited to
    # silently drop a condition.
    check = pd.read_sql_query(
        """
        SELECT s.sample_id
        FROM samples s
        JOIN subjects su ON s.subject_id = su.subject_id
        WHERE su.condition = 'melanoma'
          AND s.sample_type = 'PBMC'
          AND s.treatment = 'miraclib'
          AND s.time_from_treatment_start = 0
        """,
        conn,
    )
    assert set(baseline["sample_id"]) == set(check["sample_id"])


def test_avg_b_cell_matches_reported_value(conn):
    # Locks in the headline Part 4 answer reported in the README/output
    # (output/part4_summary.txt) as a regression guard against this query,
    # the schema, or cell-count.csv changing silently.
    b_cells = pd.read_sql_query(AVG_B_CELL_QUERY, conn)
    avg = round(b_cells["b_cell_count"].mean(), 2)
    assert len(b_cells) == 485
    assert avg == 10206.15
