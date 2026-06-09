import pytest
from unittest.mock import MagicMock
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


def test_find_domain_group_from_store():
    """Quando o store retorna domain_contexts customizados, usa-os."""
    mock_store = MagicMock()
    mock_store.get_domain_contexts.return_value = [
        {"domain_name": "fgts", "semantic_groups": {"empreendimento": ["cd_empreendimento", "id_empreend"]}, "key_patterns": {}}
    ]
    result = find_domain_group("cd_empreendimento", store=mock_store)
    assert result == "empreendimento"


def test_find_domain_group_store_fallback_to_builtin():
    """Se store retorna lista vazia, cai no builtin."""
    mock_store = MagicMock()
    mock_store.get_domain_contexts.return_value = []
    result = find_domain_group("nr_empenho", store=mock_store)
    assert result == "empenho"


def test_find_domain_group_no_store_uses_builtin():
    """Sem store (None), comportamento original mantido."""
    assert find_domain_group("nr_empenho") == "empenho"
    assert find_domain_group("coluna_desconhecida_xyz") is None


def test_find_domain_group_store_merges_with_builtin():
    """Groups do store são mesclados com builtin — builtin não é perdido."""
    mock_store = MagicMock()
    mock_store.get_domain_contexts.return_value = [
        {"domain_name": "custom", "semantic_groups": {"fgts_contrato": ["nr_contrato_fgts"]}, "key_patterns": {}}
    ]
    # campo builtin ainda funciona
    assert find_domain_group("nr_empenho", store=mock_store) == "empenho"
    # campo do store customizado também funciona
    assert find_domain_group("nr_contrato_fgts", store=mock_store) == "fgts_contrato"
