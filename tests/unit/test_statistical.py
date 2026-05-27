import pandas as pd
from src.analyzers.statistical import match_rate, overlap_stats


def test_match_rate_full():
    a = pd.Series(["ABC", "DEF", "GHI"])
    b = pd.Series(["ABC", "DEF", "GHI", "XYZ"])
    assert match_rate(a, b, normalize=False) == 1.0


def test_match_rate_partial():
    a = pd.Series(["ABC", "ZZZ"])
    b = pd.Series(["ABC"])
    rate = match_rate(a, b, normalize=False)
    assert rate == 0.5


def test_overlap_stats():
    a = pd.Series(["A", "B", "C"])
    b = pd.Series(["B", "C", "D"])
    stats = overlap_stats(a, b, normalize=False)
    assert stats["intersection"] == 2
