"""
Componente 2 — dbt Source Generator (Costura B: dbt config-driven).

Responsabilidade: ler os YAMLs do Source Registry (ingestion/configs/) e gerar
`sources.yml` + um model bronze `.sql` por fonte, sem SQL escrito à mão. Fecha a
Costura B — o achado central da PoC.

Decisão (ADR 0010): gera a partir do Source Registry (config-as-source-of-truth),
NÃO por introspecção do banco como o dbt-codegen oficial. É a contribuição original
do TCC e o que sustenta a tese de portabilidade por configuração.

Destino real: ingestion/dags/dbt_source_generator.py (ou transformation/).
Segue o mesmo padrão de transformation_dag_factory.py, que já lê os YAMLs.

NOTA: stub — assinaturas e responsabilidades definidas; lógica não preenchida.
"""
from __future__ import annotations

from pathlib import Path

import yaml

# Template do model bronze — um SELECT * sobre o source gerado.
# Espelha o que foi escrito à mão na PoC (transformation/models/bronze/ibge_municipios.sql).
BRONZE_MODEL_TEMPLATE = """\
-- GERADO por dbt_source_generator a partir de {config_file}. NÃO editar à mão.
{{{{ config(materialized='incremental', on_schema_change='sync_all_columns') }}}}

select * from {{{{ source('{source_group}', '{table}') }}}}
"""


def load_configs(configs_dir: Path) -> list[dict]:
    """Carrega todos os YAMLs do Source Registry.

    TODO: reusar a lógica de transformation_dag_factory.py (helpers de carregamento).
    Retorna a lista de dicts de config."""
    raise NotImplementedError


def build_sources_yml(configs: list[dict], source_group: str = "silver") -> str:
    """Gera o conteúdo de sources.yml a partir dos configs.

    Cada fonte vira uma entrada em `tables:` sob o source `source_group`.
    TODO: implementar — montar o dict e serializar com yaml.safe_dump.

    Estrutura alvo:
        version: 2
        sources:
          - name: <source_group>
            schema: silver
            tables:
              - name: <target_table de cada config>
    """
    raise NotImplementedError


def build_bronze_model(cfg: dict, config_file: str, source_group: str = "silver") -> str:
    """Renderiza o model bronze .sql de UMA fonte usando BRONZE_MODEL_TEMPLATE.

    TODO: extrair table = cfg['target_table'] e formatar o template."""
    raise NotImplementedError


def generate(configs_dir: Path, out_dir: Path, source_group: str = "silver") -> list[Path]:
    """Orquestra a geração completa.

    1. configs = load_configs(configs_dir)
    2. escreve out_dir/sources.yml = build_sources_yml(configs)
    3. para cada cfg: escreve out_dir/<target_table>.sql = build_bronze_model(cfg)
    4. retorna a lista de arquivos gerados

    Idempotente: regenerar sobrescreve os arquivos gerados (marcados no header).
    TODO: implementar. Cuidar para NÃO sobrescrever models silver/gold escritos à mão.
    """
    raise NotImplementedError


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Gera sources.yml + models bronze do Source Registry")
    p.add_argument("--configs", required=True, type=Path, help="Diretório dos YAMLs (ingestion/configs)")
    p.add_argument("--out", required=True, type=Path, help="Saída (transformation/models/bronze)")
    p.add_argument("--source-group", default="silver")
    args = p.parse_args()
    generate(args.configs, args.out, args.source_group)
