"""
Transformation DAG Factory — gera um DAG por pacote dbt declarado nos Source Registry YAMLs.

Substitui transformation_dag.py (manual, roda tudo) por DAGs por pacote com --select
dinâmico via ContextResolver.

Design
------
- ``collect_dbt_packages`` e ``get_dbt_select`` são funções puras sem dependências de
  Airflow/cosmos; podem ser importadas e testadas sem o ambiente Airflow.
- O bloco de geração de DAGs (loop ``for _pkg_name …``) é protegido por um
  ``try/except ImportError`` para que o módulo seja importável no ambiente de testes,
  onde ``airflow`` não está instalado.
- Cada DAG é agendado via ``Dataset`` produzido pela ingestão correspondente (data-aware
  scheduling), em vez de cron fixo, garantindo que a transformação só dispare após
  atualização real do silver layer.
- O ``ContextResolver`` é instanciado com ``store=None`` até a integração com
  ``ContextStore`` ser ativada em produção; enquanto isso, ``get_dbt_select`` retorna
  ``"models/bronze/"`` como fallback seguro.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Funções puras — sem dependências de Airflow/cosmos (testáveis em isolamento)
# ──────────────────────────────────────────────────────────────────────────────

def collect_dbt_packages(configs: list[dict]) -> dict:
    """Agrupa pacotes dbt declarados nos Source Registry configs.

    Parameters
    ----------
    configs:
        Lista de dicts carregados dos YAMLs de ``configs/``.

    Returns
    -------
    dict
        ``{package_name: {"datasets": [uri, …], "select": path}}``

        Dois configs que declaram o mesmo ``package_name`` têm seus datasets
        acumulados na mesma entrada (deduplicação por pacote, não por fonte).
    """
    packages: dict[str, dict] = {}
    for cfg in configs:
        for pkg in cfg.get("dbt_packages", []):
            name = pkg["name"]
            if name not in packages:
                packages[name] = {
                    "datasets": [],
                    "select": pkg.get("select", "models/"),
                }
            dataset_uri = cfg.get("silver_dataset")
            if dataset_uri:
                packages[name]["datasets"].append(dataset_uri)
    return packages


def get_dbt_select(package_name: str, resolver=None) -> str:
    """Retorna o caminho ``--select`` para o pacote dbt.

    Delega ao ``ContextResolver`` quando disponível; retorna ``"models/bronze/"``
    como fallback seguro quando ``resolver`` é ``None`` (ex.: ambiente de dev/test
    sem banco de contexto).

    Parameters
    ----------
    package_name:
        Identificador do pacote dbt.
    resolver:
        Instância de ``ContextResolver`` ou ``None``.

    Returns
    -------
    str
        Caminho ``--select`` a ser passado ao ``DbtTaskGroup``.
    """
    if resolver is None:
        return "models/bronze/"
    return resolver.get_select(package_name)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de carregamento de configs
# ──────────────────────────────────────────────────────────────────────────────

CONFIGS_DIR = Path("/opt/airflow/configs")
TRANSFORMATION_DIR = Path("/opt/airflow/transformation")


def _load_configs() -> list[dict]:
    """Carrega todos os YAMLs de CONFIGS_DIR; ignora arquivos malformados."""
    import yaml
    configs = []
    for f in CONFIGS_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text())
            if isinstance(data, dict):
                configs.append(data)
        except Exception:
            pass
    return configs


# ──────────────────────────────────────────────────────────────────────────────
# Geração dos DAGs — protegida por ImportError para ambiente sem Airflow
# ──────────────────────────────────────────────────────────────────────────────

try:
    from datetime import datetime

    from airflow.datasets import Dataset
    from airflow.decorators import dag

    sys.path.insert(0, "/opt/airflow")
    sys.path.insert(0, "/opt/airflow/agent_src")

    for _pkg_name, _pkg_info in collect_dbt_packages(_load_configs()).items():
        _dataset_uris = _pkg_info["datasets"]
        _schedule = [Dataset(uri) for uri in _dataset_uris] if _dataset_uris else None

        @dag(
            dag_id=f"transform_{_pkg_name}",
            schedule=_schedule,
            start_date=datetime(2025, 1, 1),
            catchup=False,
            tags=["transformation", "dbt", _pkg_name],
            default_args={"retries": 2},
        )
        def _make_transformation_dag(pkg_name=_pkg_name):
            try:
                from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig

                # ContextResolver com store=None até integração com ContextStore em produção
                resolver = None
                dbt_select = get_dbt_select(pkg_name, resolver)

                DbtTaskGroup(
                    group_id=f"dbt_{pkg_name}",
                    project_config=ProjectConfig(
                        TRANSFORMATION_DIR / "dbt_packages" / pkg_name
                    ),
                    profile_config=ProfileConfig(
                        profiles_yml_filepath=TRANSFORMATION_DIR / "profiles.yml",
                        profile_name="gov_hub",
                        target_name="prod",
                    ),
                    execution_config=ExecutionConfig(dbt_executable_path="dbt"),
                    operator_args={"select": dbt_select},
                )
            except ImportError:
                # cosmos não instalado — DAG vazio para evitar erro de parsing
                pass

        globals()[f"transform_{_pkg_name}"] = _make_transformation_dag()

except ImportError:
    # airflow não instalado (ex.: ambiente de testes) — módulo importável normalmente
    pass
