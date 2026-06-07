import pytest
from src.analyzers.semantic import normalize_col_name, name_similarity, semantic_score, find_domain_group


def test_normalize_col_name():
    assert normalize_col_name("  Nr_Empenho ") == "nr_empenho"
    assert normalize_col_name("CD.ORGAO") == "cd_orgao"


def test_name_similarity_identical():
    assert name_similarity("nr_empenho", "nr_empenho") == 1.0


def test_name_similarity_different():
    assert name_similarity("nr_empenho", "cd_orgao") < 0.5


def test_find_domain_group_exact():
    assert find_domain_group("nr_empenho") == "empenho"
    assert find_domain_group("cd_orgao") == "orgao"


def test_semantic_score_same_group():
    score = semantic_score("nr_empenho", "num_empenho")
    assert score >= 0.75
