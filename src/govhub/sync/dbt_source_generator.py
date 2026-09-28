"""
Costura B — dbt config-driven: gera sources e models bronze a partir do Source Registry.

Para cada fonte do registry, gera em ``dbt/models/bronze/_generated/``:

- ``_sources.yml``          source ``registry`` (schema ``silver``) com uma tabela por fonte;
- ``<target_table>.sql``    model bronze incremental sobre essa tabela.

Decisão (ADR 0010): gera a partir do YAML (config como fonte da verdade), e não por
introspecção do banco como o ``dbt-codegen``. É o que sustenta a tese de
portabilidade por configuração.

Regras de convivência com o código escrito à mão:

- só escreve em ``_generated/`` e só sobrescreve/remove arquivos com o cabeçalho GERADO;
- se já existe um model manual com o mesmo nome, a fonte é pulada (o manual prevalece);
- o source se chama ``registry`` para não colidir com o ``silver`` do sources.yml manual.

Uso: ``python -m govhub.sync.dbt_source_generator`` (ou ``make dbt-generate``).
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from govhub.ingestion import registry

log = logging.getLogger(__name__)

GENERATED_DIRNAME = "_generated"
SOURCES_FILENAME = "_sources.yml"
SOURCE_GROUP = "registry"
MARKER = "GERADO por govhub.sync.dbt_source_generator"

BRONZE_MODEL_TEMPLATE = """\
-- {marker} a partir de {config_file}. NÃO editar à mão.
{{{{
  config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='_silver_table',
    on_schema_change='append_new_columns'
  )
}}}}

select *
from {{{{ source('{source_group}', '{table}') }}}}

{{% if is_incremental() %}}
  where dt_ingest > (select coalesce(max(dt_ingest), '1900-01-01'::timestamptz) from {{{{ this }}}})
{{% endif %}}
"""


def source_tables(cfg: dict) -> list[str]:
    """Tabelas que a fonte grava em ``silver.*`` no Postgres.

    Dumps gravam uma tabela por entrada de ``tables``; as demais fontes, uma
    tabela ``target_table``.
    """
    if cfg.get("type") == "dump":
        return [registry.normalize_name(t) for t in cfg.get("tables") or []]
    return [registry.target_table(cfg)]


def collect_tables(configs: list[dict]) -> dict[str, str]:
    """``{tabela: arquivo_de_config}``, na ordem do registry, sem duplicatas."""
    tables: dict[str, str] = {}
    for cfg in configs:
        config_file = cfg.get(registry.CONFIG_FILE_KEY, cfg["source_name"])
        for table in source_tables(cfg):
            if table in tables:
                log.warning("Tabela %s declarada por %s e %s; mantendo a primeira",
                            table, tables[table], config_file)
                continue
            tables[table] = config_file
    return tables


def build_sources_yml(tables: dict[str, str], source_group: str = SOURCE_GROUP) -> str:
    """Conteúdo do ``_sources.yml`` com uma entrada por tabela."""
    doc = {
        "version": 2,
        "sources": [{
            "name": source_group,
            "description": "Tabelas sincronizadas pelo Silver Sync (costura A), "
                           "declaradas no Source Registry (airflow/configs/).",
            "schema": "silver",
            "tables": [
                {"name": table, "description": f"Fonte declarada em {config_file}"}
                for table, config_file in tables.items()
            ],
        }],
    }
    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    return f"# {MARKER}. NÃO editar à mão.\n{body}"


def build_bronze_model(table: str, config_file: str, source_group: str = SOURCE_GROUP) -> str:
    """SQL do model bronze incremental de uma tabela."""
    return BRONZE_MODEL_TEMPLATE.format(
        marker=MARKER, config_file=config_file, source_group=source_group, table=table
    )


def _is_generated(path: Path) -> bool:
    try:
        return MARKER in path.read_text().splitlines()[0]
    except (IndexError, OSError):
        return False


def _handwritten_models(models_dir: Path) -> set[str]:
    return {
        p.stem for p in models_dir.rglob("*.sql") if GENERATED_DIRNAME not in p.parts
    }


def generate(configs_dir: Path, models_dir: Path, source_group: str = SOURCE_GROUP) -> list[Path]:
    """Gera (ou atualiza) ``<models_dir>/bronze/_generated/``. Idempotente.

    Retorna os arquivos escritos. Remove arquivos gerados de fontes que saíram do
    registry; nunca toca em arquivo sem o cabeçalho GERADO.
    """
    out_dir = models_dir / "bronze" / GENERATED_DIRNAME
    handwritten = _handwritten_models(models_dir)

    tables = {}
    for table, config_file in collect_tables(registry.load_configs(configs_dir)).items():
        if table in handwritten:
            log.warning("Model manual '%s' já existe; fonte %s não será gerada", table, config_file)
            continue
        tables[table] = config_file

    wanted: dict[Path, str] = {
        out_dir / f"{table}.sql": build_bronze_model(table, config_file, source_group)
        for table, config_file in tables.items()
    }
    if tables:
        wanted[out_dir / SOURCES_FILENAME] = build_sources_yml(tables, source_group)

    out_dir.mkdir(parents=True, exist_ok=True)
    for path in list(out_dir.glob("*.sql")) + list(out_dir.glob("*.yml")):
        if path not in wanted and _is_generated(path):
            path.unlink()

    written = []
    for path, content in wanted.items():
        if path.exists() and not _is_generated(path):
            log.warning("%s existe e não é gerado; mantido intacto", path)
            continue
        if not path.exists() or path.read_text() != content:
            path.write_text(content)
        written.append(path)
    return written


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Gera sources.yml + models bronze do Source Registry")
    p.add_argument("--configs", type=Path, default=Path("airflow/configs"),
                   help="Diretório dos YAMLs (padrão: airflow/configs)")
    p.add_argument("--models-dir", type=Path, default=Path("dbt/models"),
                   help="Diretório models/ do projeto dbt (padrão: dbt/models)")
    p.add_argument("--source-group", default=SOURCE_GROUP)
    args = p.parse_args()
    files = generate(args.configs, args.models_dir, args.source_group)
    print(f"{len(files)} arquivo(s) em {args.models_dir / 'bronze' / GENERATED_DIRNAME}")
