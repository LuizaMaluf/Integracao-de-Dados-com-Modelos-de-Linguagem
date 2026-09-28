"""
Source Registry — leitura dos YAMLs de fonte e regras derivadas deles.

Único lugar que conhece o contrato do YAML. DAGs de ingestão, a DAG factory de
transformação e o gerador de sources do dbt (costura B) leem as fontes por aqui,
para que o nome da tabela e o dataset publicados sejam sempre os mesmos.

Campos do contrato usados pelas costuras (todos opcionais):

- ``target_table``   nome estável da tabela no schema ``silver`` do Postgres.
                     Padrão: ``source_name`` normalizado.
- ``silver_dataset`` URI do Dataset Airflow publicado após a sincronização.
                     Padrão: ``silver://<target_table>``.
- ``dbt_packages``   pacotes dbt disparados quando o dataset é atualizado.

Ver ADR 0008.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

DEFAULT_CONFIGS_DIR = Path(os.environ.get("GOVHUB_CONFIGS_DIR", "/opt/airflow/configs"))

# Chave injetada em cada config com o nome do arquivo de origem.
CONFIG_FILE_KEY = "_config_file"


def normalize_name(name: str) -> str:
    """Normaliza um identificador para uso como nome de tabela/coluna."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


def load_configs(
    configs_dir: Path | str | None = None,
    *,
    types: tuple[str, ...] | None = None,
    extraction_mode: str | None = None,
) -> list[dict]:
    """Carrega os YAMLs do registry, em ordem alfabética de arquivo.

    Arquivos malformados ou que não são um mapeamento são ignorados.
    ``types`` e ``extraction_mode`` filtram pelas chaves ``type`` e
    ``extraction_mode`` do YAML.
    """
    configs_dir = Path(configs_dir) if configs_dir else DEFAULT_CONFIGS_DIR
    configs = []
    for f in sorted(configs_dir.glob("*.yaml")):
        try:
            cfg = yaml.safe_load(f.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(cfg, dict):
            continue
        if types and cfg.get("type") not in types:
            continue
        if extraction_mode and cfg.get("extraction_mode") != extraction_mode:
            continue
        cfg[CONFIG_FILE_KEY] = f.name
        configs.append(cfg)
    return configs


def target_table(cfg: dict) -> str:
    """Nome estável da tabela da fonte no Postgres (sem sufixo de data)."""
    return normalize_name(cfg.get("target_table") or cfg["source_name"])


def silver_dataset(cfg: dict) -> str:
    """URI do Dataset Airflow que sinaliza atualização da fonte no silver."""
    return cfg.get("silver_dataset") or f"silver://{target_table(cfg)}"
