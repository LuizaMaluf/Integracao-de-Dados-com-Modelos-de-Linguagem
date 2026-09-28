"""
Integration Bridge: loads two silver tables and calls IntegrationAgent.run(),
writing the result to the output directory.

``source="duckdb"`` (padrão) lê os lotes do silver DuckDB; ``source="postgres"``
lê ``silver.<tabela>`` no PostgreSQL via PostgresLoader (costura C).
"""
import json
from pathlib import Path

from govhub.ingestion.storage import silver
from govhub.integration.agent.orchestrator import IntegrationAgent


OUTPUT_DIR = Path("/opt/airflow/output")


def _load(table: str, source: str):
    if source == "postgres":
        from govhub.integration.loaders.postgres_loader import PostgresLoader

        return PostgresLoader().load(table)
    if source != "duckdb":
        raise ValueError(f"source deve ser 'duckdb' ou 'postgres', não {source!r}")
    df = silver.read(table)
    return df, silver.build_metadata(df, table)


def run_integration(
    table_a: str, table_b: str, use_llm: bool = True, store=None, source: str = "duckdb"
) -> Path:
    """
    Load two silver tables, run IntegrationAgent, and persist the result JSON.
    Returns the output file path.
    """
    df_a, meta_a = _load(table_a, source)
    df_b, meta_b = _load(table_b, source)

    agent = IntegrationAgent(use_llm=use_llm)
    result = agent.run(df_a, meta_a, df_b, meta_b)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"identificar_chave_{meta_a.name}__{meta_b.name}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    if store is not None:
        from govhub.ingestion.bridge.context_writer import persist_discovery
        persist_discovery(result, store)

    return out_path
