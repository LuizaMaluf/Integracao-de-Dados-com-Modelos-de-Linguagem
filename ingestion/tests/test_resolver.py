import pytest
from unittest.mock import MagicMock
from context.resolver import ContextResolver


def make_resolver(discoveries):
    store = MagicMock()
    store.get_discoveries.return_value = discoveries
    return ContextResolver(store)


def test_no_discoveries_returns_bronze_only():
    """Sem integrações confirmadas, roda só bronze."""
    resolver = make_resolver([])
    assert resolver.get_select("mir") == "models/bronze/"


def test_with_discovery_returns_all_models():
    """Com pelo menos uma discovery confirmada, roda todos os modelos."""
    resolver = make_resolver([{"table_a": "mir.empenhos", "column_a": "nr_empenho",
                               "table_b": "siafi.notas_empenho", "column_b": "num_empenho",
                               "confidence": 0.94}])
    assert resolver.get_select("mir") == "models/"


def test_queries_store_with_correct_table_and_confidence():
    """Verifica que chama get_discoveries com os parâmetros certos."""
    store = MagicMock()
    store.get_discoveries.return_value = []
    resolver = ContextResolver(store)
    resolver.get_select("mir")
    store.get_discoveries.assert_called_once_with("mir", min_confidence=0.7)


def test_multiple_packages_independent():
    """Dois pacotes diferentes são resolvidos independentemente."""
    store = MagicMock()
    store.get_discoveries.side_effect = lambda table, **kw: (
        [{"confidence": 0.9}] if table == "mir" else []
    )
    resolver = ContextResolver(store)
    assert resolver.get_select("mir") == "models/"
    assert resolver.get_select("ipea") == "models/bronze/"


def test_get_select_list_returns_all_packages():
    """get_select_all retorna dict {package: select} para lista de pacotes."""
    store = MagicMock()
    store.get_discoveries.side_effect = lambda table, **kw: (
        [{"confidence": 0.9}] if table == "mir" else []
    )
    resolver = ContextResolver(store)
    result = resolver.get_select_all(["mir", "ipea"])
    assert result == {"mir": "models/", "ipea": "models/bronze/"}
