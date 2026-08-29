"""
Part 4: data subset analysis.

1. Baseline (time_from_treatment_start == 0) melanoma PBMC samples from
   patients treated with miraclib -- broken down by project, subject
   response, and subject sex.
2. Average B cell count for melanoma male responders at time == 0, across
   ALL sample types and treatments.

Outputs: output/part4_summary.txt (human-readable) and
output/part4_baseline_samples.csv (the raw matching sample rows).
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cell_counts.db"
SUMMARY_PATH = ROOT / "output" / "part4_summary.txt"
BASELINE_CSV_PATH = ROOT / "output" / "part4_baseline_samples.csv"

BASELINE_QUERY = """
SELECT
    s.sample_id,
    s.subject_id,
    su.project,
    s.response,
    su.sex
FROM samples s
JOIN subjects su ON s.subject_id = su.subject_id
WHERE su.condition = 'melanoma'
  AND s.sample_type = 'PBMC'
  AND s.treatment = 'miraclib'
  AND s.time_from_treatment_start = 0;
"""

# Part 4, final question: melanoma males, ALL sample_type and ALL treatment,
# responders, at time_from_treatment_start = 0.
AVG_B_CELL_QUERY = """
SELECT cc.count AS b_cell_count
FROM samples s
JOIN subjects su ON s.subject_id = su.subject_id
JOIN cell_counts cc ON cc.sample_id = s.sample_id
WHERE su.condition = 'melanoma'
  AND su.sex = 'M'
  AND s.response = 'yes'
  AND s.time_from_treatment_start = 0
  AND cc.population = 'b_cell';
"""


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        baseline = pd.read_sql_query(BASELINE_QUERY, conn)
        b_cells = pd.read_sql_query(AVG_B_CELL_QUERY, conn)
    finally:
        conn.close()

    OUTPUT_DIR = SUMMARY_PATH.parent
    OUTPUT_DIR.mkdir(exist_ok=True)
    baseline.to_csv(BASELINE_CSV_PATH, index=False)

    by_project = baseline.groupby("project")["sample_id"].nunique()

    subjects = baseline.drop_duplicates(subset="subject_id")
    by_response = subjects["response"].value_counts()
    by_sex = subjects["sex"].value_counts()

    avg_b_cell = round(b_cells["b_cell_count"].mean(), 2)
    n_samples_for_avg = len(b_cells)

    lines = []
    lines.append("Baseline (time=0) melanoma PBMC samples, miraclib-treated")
    lines.append("=" * 60)
    lines.append(f"Total samples: {len(baseline)}")
    lines.append(f"Total unique subjects: {baseline['subject_id'].nunique()}")
    lines.append("")
    lines.append("Samples per project:")
    for project, count in by_project.items():
        lines.append(f"  {project}: {count}")
    lines.append("")
    lines.append("Subjects by response:")
    for response, count in by_response.items():
        lines.append(f"  {response}: {count}")
    lines.append("")
    lines.append("Subjects by sex:")
    for sex, count in by_sex.items():
        lines.append(f"  {sex}: {count}")
    lines.append("")
    lines.append(
        "Average B cell count, melanoma males, responders, time=0, "
        "all sample types & treatments"
    )
    lines.append("-" * 60)
    lines.append(f"  n samples: {n_samples_for_avg}")
    lines.append(f"  average B cell count: {avg_b_cell:.2f}")

    summary_text = "\n".join(lines)
    SUMMARY_PATH.write_text(summary_text + "\n")

    print(summary_text)
    print(f"\nWrote {SUMMARY_PATH}")
    print(f"Wrote {BASELINE_CSV_PATH}")


if __name__ == "__main__":
    main()
