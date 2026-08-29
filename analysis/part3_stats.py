"""
Part 3: statistical comparison of cell population relative frequencies
between responders and non-responders.

Cohort: melanoma patients, treated with miraclib, PBMC samples only.

Outputs:
  output/part3_responder_comparison.csv  -- per-population summary stats + tests
  output/part3_boxplots.png              -- boxplot per population, responders vs non-responders
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cell_counts.db"
RESULTS_PATH = ROOT / "output" / "part3_responder_comparison.csv"
PLOT_PATH = ROOT / "output" / "part3_boxplots.png"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

QUERY = """
SELECT
    s.sample_id AS sample,
    s.response AS response,
    cc.population AS population,
    100.0 * cc.count / SUM(cc.count) OVER (PARTITION BY cc.sample_id) AS percentage
FROM samples s
JOIN subjects su ON s.subject_id = su.subject_id
JOIN cell_counts cc ON cc.sample_id = s.sample_id
WHERE su.condition = 'melanoma'
  AND s.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND s.response IN ('yes', 'no');
"""


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        i = n - rank + 1
        raw = p_values[idx] * n / i
        prev = min(prev, raw)
        adjusted[idx] = prev
    return [min(v, 1.0) for v in adjusted]


def load_cohort(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(QUERY, conn)


def compare_populations(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    p_values = []
    for population in POPULATIONS:
        sub = df[df["population"] == population]
        responders = sub.loc[sub["response"] == "yes", "percentage"]
        non_responders = sub.loc[sub["response"] == "no", "percentage"]

        u_stat, mw_p = stats.mannwhitneyu(
            responders, non_responders, alternative="two-sided"
        )
        t_stat, t_p = stats.ttest_ind(responders, non_responders, equal_var=False)

        rows.append(
            {
                "population": population,
                "n_responders": len(responders),
                "n_non_responders": len(non_responders),
                "median_responder_pct": round(responders.median(), 3),
                "median_non_responder_pct": round(non_responders.median(), 3),
                "mean_responder_pct": round(responders.mean(), 3),
                "mean_non_responder_pct": round(non_responders.mean(), 3),
                "mannwhitney_u": u_stat,
                "mannwhitney_p": mw_p,
                "welch_ttest_p": t_p,
            }
        )
        p_values.append(mw_p)

    result = pd.DataFrame(rows)
    result["mannwhitney_p_fdr"] = benjamini_hochberg(p_values)
    result["significant_fdr_0.05"] = result["mannwhitney_p_fdr"] < 0.05
    return result


def plot_boxplots(df: pd.DataFrame) -> None:
    np.random.seed(0)  # stripplot jitter is random; fix seed for reproducible output
    fig, axes = plt.subplots(1, len(POPULATIONS), figsize=(4 * len(POPULATIONS), 4.5), sharey=False)
    for ax, population in zip(axes, POPULATIONS):
        sub = df[df["population"] == population]
        sns.boxplot(
            data=sub,
            x="response",
            y="percentage",
            order=["no", "yes"],
            hue="response",
            hue_order=["no", "yes"],
            palette={"no": "#d95f02", "yes": "#1b9e77"},
            legend=False,
            ax=ax,
        )
        sns.stripplot(
            data=sub,
            x="response",
            y="percentage",
            order=["no", "yes"],
            color="black",
            alpha=0.25,
            size=2,
            ax=ax,
        )
        ax.set_title(population)
        ax.set_xlabel("response")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["non-responder", "responder"])
        ax.set_ylabel("% of total cells" if population == POPULATIONS[0] else "")

    fig.suptitle(
        "Melanoma + miraclib + PBMC: cell population frequency, responders vs non-responders"
    )
    fig.tight_layout()
    fig.savefig(PLOT_PATH, dpi=150)
    plt.close(fig)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = load_cohort(conn)
    finally:
        conn.close()

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    results = compare_populations(df)
    results.to_csv(RESULTS_PATH, index=False)
    plot_boxplots(df)

    print(results.to_string(index=False))
    print(f"\nWrote {RESULTS_PATH}")
    print(f"Wrote {PLOT_PATH}")


if __name__ == "__main__":
    main()
