import pandas as pd
from src.transformers.normalizer import normalize_series, pad_left, extract_digits


def test_normalize_series_strips_and_uppercases():
    s = pd.Series([" abc ", "def"])
    result = normalize_series(s)
    assert result.tolist() == ["ABC", "DEF"]


def test_normalize_removes_special_chars():
    s = pd.Series(["12.345-6", "78/90"])
    result = normalize_series(s)
    assert result.tolist() == ["123456", "7890"]


def test_pad_left():
    s = pd.Series(["123", "45"])
    result = pad_left(s, 6)
    assert result.tolist() == ["000123", "000045"]


def test_extract_digits():
    s = pd.Series(["AB-123", "456/CD"])
    result = extract_digits(s)
    assert result.tolist() == ["123", "456"]
