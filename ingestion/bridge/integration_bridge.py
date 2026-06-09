"""
Integration Bridge: loads two staged tables from DuckDB silver zone
and calls IntegrationAgent.run(), writing the result to the output directory.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/airflow/agent_src")
from agent.orchestrator import IntegrationAgent  # noqa: E402

from storage import silver


OUTPUT_DIR = Path("/opt/airflow/output")


def run_integration(table_a: str, table_b: str, use_llm: bool = True, store=None) -> Path:
    """
    Load two silver tables, run IntegrationAgent, and persist the result JSON.
    Returns the output file path.
    """
    df_a = silver.read(table_a)
    df_b = silver.read(table_b)
    meta_a = silver.build_metadata(df_a, table_a)
    meta_b = silver.build_metadata(df_b, table_b)

    agent = IntegrationAgent(use_llm=use_llm)
    result = agent.run(df_a, meta_a, df_b, meta_b)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"identificar_chave_{table_a}__{table_b}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    if store is not None:
        from bridge.context_writer import persist_discovery
        persist_discovery(result, store)

    return out_path
