import pytest
from unittest.mock import MagicMock, patch

# Configs YAML simulados
CONFIGS_WITH_DBT = [
    {"source_name": "mir_empenhos", "type": "api",
     "silver_dataset": "silver://mir_empenhos",
     "dbt_packages": [{"name": "mir", "select": "models/"}]},
    {"source_name": "ipea_dados", "type": "csv",
     "silver_dataset": "silver://ipea_dados",
     "dbt_packages": [{"name": "ipea", "select": "models/bronze/"}]},
]
CONFIGS_WITHOUT_DBT = [
    {"source_name": "aux_table", "type": "csv"},
]


def test_collect_packages_from_configs():
    """collect_dbt_packages agrupa packages por nome e seus datasets."""
    from dags.transformation_dag_factory import collect_dbt_packages
    result = collect_dbt_packages(CONFIGS_WITH_DBT + CONFIGS_WITHOUT_DBT)
    assert "mir" in result
    assert "ipea" in result
    assert "aux_table" not in result
    assert result["mir"]["datasets"] == ["silver://mir_empenhos"]


def test_collect_packages_deduplicates():
    """Dois configs declarando o mesmo pacote → merge dos datasets."""
    configs = [
        {"source_name": "mir_empenhos", "silver_dataset": "silver://mir_empenhos",
         "dbt_packages": [{"name": "mir"}]},
        {"source_name": "mir_programas", "silver_dataset": "silver://mir_programas",
         "dbt_packages": [{"name": "mir"}]},
    ]
    from dags.transformation_dag_factory import collect_dbt_packages
    result = collect_dbt_packages(configs)
    assert len(result["mir"]["datasets"]) == 2


def test_collect_skips_configs_without_dbt_packages():
    """Configs sem dbt_packages são ignorados."""
    from dags.transformation_dag_factory import collect_dbt_packages
    result = collect_dbt_packages(CONFIGS_WITHOUT_DBT)
    assert result == {}


def test_get_dbt_select_delegates_to_resolver():
    """get_dbt_select chama resolver.get_select com o package_name."""
    from dags.transformation_dag_factory import get_dbt_select
    resolver = MagicMock()
    resolver.get_select.return_value = "models/"
    result = get_dbt_select("mir", resolver)
    resolver.get_select.assert_called_once_with("mir")
    assert result == "models/"


def test_get_dbt_select_fallback_when_no_resolver():
    """Sem resolver (None), retorna 'models/bronze/' como fallback seguro."""
    from dags.transformation_dag_factory import get_dbt_select
    assert get_dbt_select("mir", resolver=None) == "models/bronze/"
