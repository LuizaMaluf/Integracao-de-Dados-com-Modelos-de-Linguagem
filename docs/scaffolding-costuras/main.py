"""
Entry point — Config-Driven E2E Bridge.

Demonstra os três componentes conectados num fluxo de ponta a ponta a partir de
UM único YAML do Source Registry. Esqueleto: instancia e liga os componentes,
sem lógica de negócio preenchida (cada chamada delega aos stubs).

Fluxo provado na Fase 5 (Preview):
  YAML → [ingestão já existe] → Silver Sync → Source Generator + dbt → Postgres Loader → IntegrationAgent
"""
from __future__ import annotations

from pathlib import Path

from dbt_source_generator import generate
from postgres_loader import PostgresLoader
from silver_sync import sync_to_postgres

CONFIGS_DIR = Path("ingestion/configs")
BRONZE_OUT = Path("transformation/models/bronze")


def run_e2e(duckdb_table: str, target_table: str, pair: tuple[str, str]) -> None:
    """Encadeia as três costuras para uma fonte recém-ingerida.

    Pré-condição: a ingestão (extract→bronze→stage_silver) já rodou e a tabela
    existe no DuckDB. Este fluxo cobre da costura A em diante.
    """
    # Costura A — sincroniza o silver DuckDB → PostgreSQL
    n = sync_to_postgres(duckdb_table, target_table)
    print(f"[A] Silver Sync: {n} linhas → silver.{target_table}")

    # Costura B — (re)gera sources.yml + models bronze a partir do Source Registry, depois dbt run
    gerados = generate(CONFIGS_DIR, BRONZE_OUT)
    print(f"[B] Source Generator: {len(gerados)} artefatos dbt gerados")
    # subprocess: dbt run --select bronze   (TODO)

    # Costura C — carrega o par direto do banco para a integração
    loader = PostgresLoader()
    df_a, meta_a = loader.load(pair[0])
    df_b, meta_b = loader.load(pair[1])
    print(f"[C] Postgres Loader: {meta_a.name} ({len(df_a)}) × {meta_b.name} ({len(df_b)})")
    # IntegrationAgent.run(df_a, meta_a, df_b, meta_b)   (TODO)


if __name__ == "__main__":
    # Exemplo: o par IBGE da PoC, agora lido do banco em vez de CSV.
    run_e2e(
        duckdb_table="ibge_municipios_20260615",
        target_table="ibge_municipios",
        pair=("silver.ibge_municipios", "silver.ibge_estados"),
    )
