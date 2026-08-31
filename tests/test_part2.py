from analysis.part2_frequencies import compute_frequencies


def test_percentages_sum_to_100_per_sample(conn):
    df = compute_frequencies(conn)
    totals = df.groupby("sample")["percentage"].sum()
    assert ((totals - 100).abs() < 0.01).all()


def test_every_sample_has_all_five_populations(conn):
    df = compute_frequencies(conn)
    counts = df.groupby("sample").size()
    assert (counts == 5).all()


def test_counts_are_non_negative(conn):
    df = compute_frequencies(conn)
    assert (df["count"] >= 0).all()
