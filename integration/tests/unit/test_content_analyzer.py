import pandas as pd
import pytest

from src.analyzers.content_analyzer import analyze, PROMOTION_THRESHOLD, ContentEvidence


def _series(values):
    return pd.Series(values)


# ── format_match ─────────────────────────────────────────────────────────────

def test_format_match_same_pattern():
    # Both columns match 'exercicio' (4-digit year pattern)
    years = _series(["2020", "2021", "2022"] * 30)
    ev = analyze(years, years.copy())
    # Same series → overlap 1.0, format_match True
    assert ev.format_match is True
    assert ev.content_score >= PROMOTION_THRESHOLD


def test_format_match_different_patterns():
    years = _series(["2020", "2021"] * 50)
    # cnpj-like values — very different pattern
    cnpjs = _series(["12.345.678/0001-90"] * 100)
    ev = analyze(years, cnpjs)
    assert ev.format_match is False


# ── overlap_rate ─────────────────────────────────────────────────────────────

def test_full_overlap_promotes():
    s = _series(["ABC", "DEF", "GHI"] * 30)
    ev = analyze(s, s.copy())
    assert ev.overlap_rate == 1.0
    assert ev.promoted()


def test_zero_overlap_does_not_promote():
    a = _series(["AAA", "BBB", "CCC"] * 30)
    b = _series(["XXX", "YYY", "ZZZ"] * 30)
    ev = analyze(a, b)
    assert ev.overlap_rate == 0.0
    assert not ev.promoted()


# ── substring_match_rate ──────────────────────────────────────────────────────

def test_substring_promotes_derived_key():
    # Column A has short keys; column B has the full SIAFI identifier containing them
    short_keys = _series(["NE000123", "NE000456"] * 50)
    full_ids = _series(["123456789002023NE000123", "123456789002023NE000456"] * 50)
    ev = analyze(short_keys, full_ids)
    assert ev.substring_match_rate > 0.0
    assert ev.promoted()


# ── ContentEvidence.promoted ──────────────────────────────────────────────────

def test_promoted_boundary():
    ev = ContentEvidence(
        format_match=False,
        format_a=None,
        format_b=None,
        overlap_rate=0.0,
        substring_match_rate=0.0,
        content_score=PROMOTION_THRESHOLD - 0.001,
    )
    assert not ev.promoted()

    ev2 = ContentEvidence(
        format_match=False,
        format_a=None,
        format_b=None,
        overlap_rate=0.0,
        substring_match_rate=0.0,
        content_score=PROMOTION_THRESHOLD,
    )
    assert ev2.promoted()


# ── to_dict ───────────────────────────────────────────────────────────────────

def test_to_dict_keys():
    s = _series(["A", "B"] * 50)
    ev = analyze(s, s.copy())
    d = ev.to_dict()
    assert set(d.keys()) == {
        "format_match", "format_a", "format_b",
        "overlap_rate", "substring_match_rate", "content_score",
    }
