"""
Integration Bridge: loads two staged tables from DuckDB silver zone
and calls IntegrationAgent.run(), writing the result to the output directory.
"""
import json
from pathlib import Path

from agent.orchestrator import IntegrationAgent

from storage import silver


OUTPUT_DIR = Path("/opt/airflow/output")


def run_integration(table_a: str, table_b: str, use_llm: bool = True) -> Path:
    df_a = silver.read(table_a)
    df_b = silver.read(table_b)
    meta_a = silver.build_metadata(df_a, table_a)
    meta_b = silver.build_metadata(df_b, table_b)

    agent = IntegrationAgent(use_llm=use_llm)
    result = agent.run(df_a, meta_a, df_b, meta_b)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"identificar_chave_{table_a}__{table_b}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return out_path
