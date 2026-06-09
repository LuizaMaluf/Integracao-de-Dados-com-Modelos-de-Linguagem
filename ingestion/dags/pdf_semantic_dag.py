"""
DAG: PDF semantic ingestion.
Discovers all configs of type pdf_semantic in /opt/airflow/configs/.
Flow: download PDF → write raw binary to bronze →
      unstructured layout analysis → Claude API extraction →
      write Parquet to bronze → stage to silver
On LLM failure the task is marked failed; the raw PDF remains in bronze.
"""
from airflow.decorators import dag, task

from ingestion.dags.factory import register_dags
from core.extractors.factory import get_extractor
from core.providers.factory import get_storage


def dag_factory(cfg: dict):
    @dag(
        dag_id=f"ingest_pdf_semantic_{cfg['source_name']}",
        schedule=cfg.get("schedule", "@monthly"),
        catchup=False,
        tags=["ingestion", "pdf", "semantic"],
    )
    def ingest():
        @task()
        def download_pdf() -> str:
            from storage import bronze
            pdf_bytes = get_extractor(cfg).extract()
            return bronze.write_bytes(pdf_bytes, cfg["source_name"], "source.pdf")

        @task()
        def parse_pdf(bronze_pdf_key: str) -> str:
            """Fails explicitly on invalid LLM response — raw PDF stays in bronze."""
            from storage import bronze
            from core.parsers.semantic_parser import SemanticPdfParser
            pdf_bytes = bronze.read_bytes(bronze_pdf_key)
            df = SemanticPdfParser(cfg).parse(pdf_bytes)
            if df.empty:
                raise ValueError(f"SemanticPdfParser returned empty DataFrame for {cfg['source_name']}")
            return bronze.write_parquet(df, cfg["source_name"], "parsed.parquet")

        @task()
        def stage_silver(bronze_parquet_key: str):
            from storage import bronze, silver
            df = bronze.read_parquet(bronze_parquet_key)
            return silver.write(df, cfg["source_name"])

        stage_silver(parse_pdf(download_pdf()))

    return ingest()


register_dags("pdf_semantic", dag_factory, globals())
