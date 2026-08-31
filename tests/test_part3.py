from analysis.part3_stats import POPULATIONS, benjamini_hochberg, compare_populations, load_cohort


def test_cohort_only_contains_yes_no_responses(conn):
    df = load_cohort(conn)
    assert set(df["response"].unique()) <= {"yes", "no"}


def test_compare_populations_covers_all_populations(conn):
    df = load_cohort(conn)
    result = compare_populations(df)
    assert set(result["population"]) == set(POPULATIONS)


def test_compare_populations_stats_are_in_valid_ranges(conn):
    df = load_cohort(conn)
    result = compare_populations(df)
    assert (result["mannwhitney_p"].between(0, 1)).all()
    assert (result["mannwhitney_p_fdr"].between(0, 1)).all()
    assert (result["welch_ttest_p"].between(0, 1)).all()
    assert (result["rank_biserial_r"].between(-1, 1)).all()


def test_benjamini_hochberg_known_values():
    # raw p-values with a known-by-hand BH adjustment (n=5):
    # sorted ascending: 0.005(idx3) 0.01(idx0) 0.03(idx2) 0.04(idx1) 0.5(idx4)
    # raw*n/rank:        0.025      0.025      0.05       0.05       0.5
    # running min from the largest rank down gives the adjusted values below.
    raw = [0.01, 0.04, 0.03, 0.005, 0.5]
    expected = [0.025, 0.05, 0.05, 0.025, 0.5]

    adjusted = benjamini_hochberg(raw)

    for got, want in zip(adjusted, expected):
        assert abs(got - want) < 1e-9


def test_benjamini_hochberg_bounded_and_right_length():
    raw = [0.2, 0.01, 0.6, 0.001, 0.9]
    adjusted = benjamini_hochberg(raw)
    assert len(adjusted) == len(raw)
    assert all(0 <= p <= 1 for p in adjusted)
