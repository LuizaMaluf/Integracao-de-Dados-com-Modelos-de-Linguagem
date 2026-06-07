"""
DAG: PDF semantic ingestion.
Discovers all configs of type pdf + extraction_mode: semantic.
Flow: download PDF → write raw binary to bronze →
      unstructured layout analysis → Claude API extraction →
      write Parquet to bronze → stage to silver
On LLM failure the task is marked failed; the raw PDF remains in bronze.
"""
import sys
from pathlib import Path

import yaml
from airflow.decorators import dag, task

sys.path.insert(0, "/opt/airflow")

CONFIGS_DIR = Path("/opt/airflow/configs")


def _load_configs():
    return [
        cfg
        for f in CONFIGS_DIR.glob("*.yaml")
        for cfg in [yaml.safe_load(f.read_text())]
        if cfg.get("type") == "pdf" and cfg.get("extraction_mode") == "semantic"
    ]


for _cfg in _load_configs():
    _source = _cfg["source_name"]

    @dag(
        dag_id=f"ingest_pdf_semantic_{_source}",
        schedule=_cfg.get("schedule", "@monthly"),
        catchup=False,
        tags=["ingestion", "pdf", "semantic"],
    )
    def _make_dag(cfg=_cfg):
        @task()
        def download_pdf(cfg) -> str:
            from extractors.pdf_extractor import PdfExtractor
            from storage import bronze
            pdf_bytes = PdfExtractor(cfg).extract()
            return bronze.write_bytes(pdf_bytes, cfg["source_name"], "source.pdf")

        @task()
        def parse_pdf(bronze_pdf_key: str, cfg) -> str:
            """Fails explicitly on invalid LLM response — raw PDF stays in bronze."""
            from storage import bronze
            from parsers.semantic_parser import SemanticPdfParser
            pdf_bytes = bronze.read_bytes(bronze_pdf_key)
            df = SemanticPdfParser(cfg).parse(pdf_bytes)
            if df.empty:
                raise ValueError(f"SemanticPdfParser returned empty DataFrame for {cfg['source_name']}")
            return bronze.write_parquet(df, cfg["source_name"], "parsed.parquet")

        @task()
        def stage_silver(bronze_parquet_key: str, cfg):
            from storage import bronze, silver
            df = bronze.read_parquet(bronze_parquet_key)
            return silver.write(df, cfg["source_name"])

        pdf_key = download_pdf(cfg)
        parquet_key = parse_pdf(pdf_key, cfg)
        stage_silver(parquet_key, cfg)

    globals()[f"ingest_pdf_semantic_{_source}"] = _make_dag()
