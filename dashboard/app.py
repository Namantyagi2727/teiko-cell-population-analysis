"""
Interactive dashboard for Bob Loblaw's immune cell population analysis.

Run with `streamlit run dashboard/app.py` (or `make dashboard`). If
cell_counts.db doesn't exist yet (e.g. a fresh deploy where the pipeline
hasn't been run), it's built automatically from cell-count.csv on first
load rather than failing.
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cell_counts.db"
sys.path.insert(0, str(ROOT))

import load_data  # noqa: E402
from analysis.part3_stats import POPULATIONS, compare_populations  # noqa: E402

st.set_page_config(page_title="Loblaw Bio - Immune Cell Analysis", layout="wide")


@st.cache_data
def load_frequencies() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
        SELECT
            cc.sample_id AS sample,
            s.subject_id, su.project, su.condition, su.sex, su.age,
            s.treatment, s.response, s.sample_type, s.time_from_treatment_start,
            cc.population,
            cc.count,
            100.0 * cc.count / SUM(cc.count) OVER (PARTITION BY cc.sample_id) AS percentage
        FROM cell_counts cc
        JOIN samples s ON cc.sample_id = s.sample_id
        JOIN subjects su ON s.subject_id = su.subject_id
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def distinct_values(df: pd.DataFrame, col: str) -> list:
    return sorted(v for v in df[col].dropna().unique())


if not DB_PATH.exists():
    with st.spinner("First run: building cell_counts.db from cell-count.csv..."):
        load_data.main()

data = load_frequencies()

st.title("Immune Cell Population Analysis")
st.caption("Loblaw Bio - miraclib clinical trial")

tab2, tab3, tab4 = st.tabs(
    ["Part 2 - Frequencies", "Part 3 - Responder Analysis", "Part 4 - Baseline Subset"]
)

# ---------------------------------------------------------------- Part 2 ---
with tab2:
    st.subheader("Relative frequency of each cell population per sample")

    samples = distinct_values(data, "sample")
    selected_sample = st.selectbox(
        "Filter to a single sample (optional)", ["All samples"] + samples
    )

    freq_df = data[
        ["sample", "population", "count", "percentage"]
    ].copy()
    freq_df["total_count"] = data.groupby("sample")["count"].transform("sum")
    freq_df = freq_df[["sample", "total_count", "population", "count", "percentage"]]

    if selected_sample != "All samples":
        freq_df = freq_df[freq_df["sample"] == selected_sample]

    freq_df = freq_df.sort_values(["sample", "population"])
    st.dataframe(freq_df, width="stretch", height=400)
    st.download_button(
        "Download this table (CSV)",
        data=freq_df.to_csv(index=False),
        file_name="part2_frequencies.csv",
        mime="text/csv",
    )

    avg_composition = (
        data.groupby("population")["percentage"].mean().reindex(POPULATIONS).reset_index()
    )
    fig = px.bar(
        avg_composition,
        x="population",
        y="percentage",
        title="Average population composition across all samples",
        labels={"percentage": "mean % of total cells"},
    )
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- Part 3 ---
with tab3:
    st.subheader("Responders vs non-responders")
    st.caption(
        "Default cohort per Bob's question: melanoma, miraclib, PBMC samples. "
        "Filters below let you explore other cohorts."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        condition = st.selectbox(
            "condition", distinct_values(data, "condition"),
            index=distinct_values(data, "condition").index("melanoma")
            if "melanoma" in distinct_values(data, "condition") else 0,
        )
    with col2:
        treatments = distinct_values(data[data["condition"] == condition], "treatment")
        treatment = st.selectbox(
            "treatment", treatments, index=treatments.index("miraclib") if "miraclib" in treatments else 0
        )
    with col3:
        sample_types = distinct_values(
            data[(data["condition"] == condition) & (data["treatment"] == treatment)],
            "sample_type",
        )
        sample_type = st.selectbox(
            "sample_type", sample_types, index=sample_types.index("PBMC") if "PBMC" in sample_types else 0
        )

    cohort = data[
        (data["condition"] == condition)
        & (data["treatment"] == treatment)
        & (data["sample_type"] == sample_type)
        & (data["response"].isin(["yes", "no"]))
    ]

    if cohort.empty:
        st.warning("No samples match this combination of filters.")
    else:
        fig = px.box(
            cohort,
            x="population",
            y="percentage",
            color="response",
            category_orders={"population": POPULATIONS, "response": ["no", "yes"]},
            color_discrete_map={"no": "#d95f02", "yes": "#1b9e77"},
            points="outliers",
            labels={"percentage": "% of total cells"},
            title=f"{condition} / {treatment} / {sample_type}: responders vs non-responders",
        )
        st.plotly_chart(fig, width="stretch")

        stats_df = compare_populations(
            cohort.rename(columns={"sample": "sample_id"})[["population", "response", "percentage"]]
        )
        st.markdown("**Statistical comparison** (Mann-Whitney U, Benjamini-Hochberg FDR-adjusted)")
        st.caption(
            "`rank_biserial_r` is the effect size (-1 to 1); check this alongside "
            "the p-value since large n can make tiny differences \"significant\"."
        )
        st.dataframe(stats_df, width="stretch")
        st.download_button(
            "Download this comparison (CSV)",
            data=stats_df.to_csv(index=False),
            file_name="part3_responder_comparison.csv",
            mime="text/csv",
        )
        st.caption(
            "To save a chart image, use the camera icon in the plot's own toolbar "
            "(top-right, on hover)."
        )

# ---------------------------------------------------------------- Part 4 ---
with tab4:
    st.subheader("Baseline melanoma PBMC samples, miraclib-treated")

    baseline = data[
        (data["condition"] == "melanoma")
        & (data["sample_type"] == "PBMC")
        & (data["treatment"] == "miraclib")
        & (data["time_from_treatment_start"] == 0)
    ].drop_duplicates(subset="sample")

    subjects = baseline.drop_duplicates(subset="subject_id")

    m1, m2, m3 = st.columns(3)
    m1.metric("Baseline samples", baseline["sample"].nunique())
    m2.metric("Unique subjects", subjects["subject_id"].nunique())
    m3.metric("Projects represented", subjects["project"].nunique())

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Samples per project**")
        st.dataframe(baseline.groupby("project")["sample"].nunique().rename("samples"))
    with c2:
        st.markdown("**Subjects by response**")
        st.dataframe(subjects["response"].value_counts().rename("subjects"))
    with c3:
        st.markdown("**Subjects by sex**")
        st.dataframe(subjects["sex"].value_counts().rename("subjects"))

    st.divider()
    st.markdown(
        "**Average B cell count** - melanoma males, responders, time=0, "
        "all sample types & treatments"
    )
    b_cell_subset = data[
        (data["condition"] == "melanoma")
        & (data["sex"] == "M")
        & (data["response"] == "yes")
        & (data["time_from_treatment_start"] == 0)
        & (data["population"] == "b_cell")
    ]
    avg_b_cell = b_cell_subset["count"].mean()
    st.metric("Average B cell count", f"{avg_b_cell:.2f}", help=f"n = {len(b_cell_subset)} samples")

    st.divider()
    baseline_export = baseline[["sample", "subject_id", "project", "response", "sex"]]
    st.download_button(
        "Download baseline sample list (CSV)",
        data=baseline_export.to_csv(index=False),
        file_name="part4_baseline_samples.csv",
        mime="text/csv",
    )
