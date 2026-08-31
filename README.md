# Immune Cell Population Analysis

Analysis pipeline and interactive dashboard for Bob Loblaw's miraclib clinical
trial data, built on the cell population counts in `cell-count.csv`.

**Live dashboard:** _TODO_ (deployed via Streamlit Community Cloud)

## Running it

Everything below works unmodified in a fresh GitHub Codespace.

```bash
make setup      # installs dependencies from requirements.txt
make pipeline   # builds the SQLite DB and generates every output table/plot
make dashboard  # starts the interactive dashboard (Streamlit, port 8501)
```

`make pipeline` runs, in order:

1. `python3 load_data.py` — creates `cell_counts.db` in the repo root from
   `cell-count.csv`.
2. `python3 analysis/part2_frequencies.py` — writes `output/part2_frequencies.csv`.
3. `python3 analysis/part3_stats.py` — writes `output/part3_responder_comparison.csv`
   and `output/part3_boxplots.png`.
4. `python3 analysis/part4_subset.py` — writes `output/part4_summary.txt` and
   `output/part4_baseline_samples.csv`.

Generated `.db` files and everything in `output/` are also checked into this
repo so results can be inspected without running anything, but they're fully
reproducible by re-running `make pipeline` (the pipeline is deterministic —
re-running it produces byte-identical output).

`make dashboard` needs `cell_counts.db` to already exist, so run `make
pipeline` at least once first. In Codespaces, accept the port-forwarding
prompt for port 8501 to open it in the browser.

## Database schema

Three normalized tables:

```
subjects(subject_id PK, project, condition, age, sex)
samples(sample_id PK, subject_id FK -> subjects, treatment, response,
        sample_type, time_from_treatment_start)
cell_counts(sample_id FK -> samples, population, count)   -- PK (sample_id, population)
```

`subjects` holds attributes that are constant per patient (verified against
the data — a given `subject_id` always has the same `project`, `condition`,
`age`, `sex`). `samples` holds one row per biological sample, since
`treatment`, `response`, `sample_type`, and timepoint vary sample-to-sample.
`cell_counts` stores counts in **long format** — one row per
`(sample, population)` pair — rather than one column per population.

Note: the assignment text refers to `indication` and `gender`; the actual
CSV columns are named `condition` and `sex`. The schema follows the CSV's
real column names.

### Why this design

- **Normalization avoids redundancy and update anomalies.** A wide,
  denormalized table (one row per sample with subject fields repeated) would
  duplicate `project`/`condition`/`age`/`sex` across every sample from the
  same subject. Fixing a data-entry error would mean updating N rows instead
  of one.
- **Long format for `cell_counts` scales with the panel, not against it.**
  Adding a sixth population (e.g. a `treg_cell` column) requires zero schema
  changes — just more rows. A wide table (`b_cell, cd8_t_cell, ...` as
  columns) needs an `ALTER TABLE` and a backfill decision for every existing
  sample every time the panel changes. Long format also handles samples that
  don't have every population measured (sparse panels) without nullable
  columns.
- **Foreign keys + indexes on `subject_id`/`sample_id`** keep the natural
  join path (`cell_counts -> samples -> subjects`) fast and enforce
  referential integrity.

### Scaling to hundreds of projects / thousands of samples / more analytics

The row-based design already scales structurally — more projects and
samples are just more rows, not new tables or columns, and the two indexes
(`idx_samples_subject`, `idx_cellcounts_sample`) keep joins fast well past
this dataset's size. Beyond that, for a real multi-project deployment I
would:

- **Move off SQLite to Postgres** once there's concurrent read/write access
  from multiple pipelines or dashboard users — SQLite's single-writer model
  is fine for a local pipeline/dashboard like this one, not for a shared
  service.
- **Promote `project` to its own `projects` table** (project_id, PI, start
  date, indications studied, ...) instead of a free-text column on
  `subjects`. That kills typo-driven duplicates (`"prj1"` vs `"Prj1"`) and
  gives a place to hang project-level metadata.
- **Add a `populations` reference table** (population_id, name, panel/assay
  version, unit) if the measured populations start varying by assay or
  project, instead of treating `population` as a bare string.
- **Precompute the Part 2 frequency table as a materialized table/view**
  (or refresh it as an ETL step in `load_data.py`) rather than recomputing
  the window-function percentage on every query, once sample counts get
  large enough that repeated ad hoc joins over raw counts get slow.
- **Keep new, study-specific fields as typed columns when they're common
  across studies**, and reach for a sparse key-value extension table only
  for genuinely one-off per-project fields — a full EAV model trades away
  type-safety and indexability and isn't worth it for fields most projects
  share.

In short: `subjects` / `samples` / `cell_counts` is already a small
fact-and-dimensions layout (`cell_counts` as the fact table, `subjects` and
`samples` as dimensions) — scaling it up mostly means adding more dimension
tables (`projects`, `populations`) rather than restructuring what's there.

## Code structure

```
load_data.py                          # Part 1: schema + CSV loader (root, per spec)
analysis/
  part2_frequencies.py                # Part 2: per-sample population frequencies
  part3_stats.py                      # Part 3: responder vs non-responder comparison
  part4_subset.py                     # Part 4: baseline subset breakdown + B-cell average
dashboard/
  app.py                              # Streamlit dashboard, covers Parts 2-4
output/                                # generated tables + plots (see below)
cell_counts.db                        # generated SQLite database
requirements.txt
Makefile
```

Each part lives in its own script rather than one monolithic file so it can
be run, read, and debugged independently — `make pipeline` just runs them
back to back. The dashboard imports `compare_populations` directly from
`analysis/part3_stats.py` instead of reimplementing the statistics, so the
batch pipeline output and the live dashboard numbers can't drift apart.

### Part 3 methodology

Cohort: melanoma, miraclib-treated, PBMC samples only, restricted to
samples with a `yes`/`no` response. For each of the 5 populations,
responders vs non-responders are compared with a **Mann-Whitney U test**
(the primary test — percentage/compositional data isn't guaranteed normal,
and the test is robust to outliers), with a **Welch's t-test** reported
alongside for reference. Since 5 populations are tested simultaneously, raw
p-values are adjusted with **Benjamini-Hochberg FDR correction**; see
`output/part3_responder_comparison.csv` for both raw and adjusted p-values.
In this dataset, no population's difference survives FDR correction at 0.05
(`cd4_t_cell` is the closest, raw p = 0.013, FDR-adjusted p = 0.067).

Because each group has ~1000 samples, a test can reach statistical
significance on a difference too small to matter practically. To guard
against over-reading a low p-value, the table also reports the
**rank-biserial correlation** (`rank_biserial_r`) as an effect size — it
ranges from -1 to 1, where 0 means no tendency for either group to skew
higher and ±1 means complete separation. Every population here has
`|r| < 0.07`, i.e. even `cd4_t_cell`'s nominally low p-value corresponds to
a negligible effect size. This is the strongest evidence to bring to Yah:
not just "nothing survives correction," but "even the raw, uncorrected
signal is too small to be a usable predictor of response."

### Part 4 answer

Average B cell count for melanoma male responders at time = 0, across all
sample types and treatments: **10206.15** (n = 485 samples). See
`output/part4_summary.txt` for the full breakdown (samples per project,
responders/non-responders, males/females among baseline melanoma/PBMC/
miraclib samples).

## Output files

| File | Description |
|---|---|
| `cell_counts.db` | SQLite database built by `load_data.py` |
| `output/part2_frequencies.csv` | Part 2 — per-sample, per-population frequency table |
| `output/part3_responder_comparison.csv` | Part 3 — per-population summary stats + significance tests |
| `output/part3_boxplots.png` | Part 3 — boxplots, responders vs non-responders, per population |
| `output/part4_summary.txt` | Part 4 — baseline subset breakdown + B-cell average |
| `output/part4_baseline_samples.csv` | Part 4 — raw matching sample rows for the baseline subset |
