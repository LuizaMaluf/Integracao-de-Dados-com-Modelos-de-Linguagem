"""
DAG: PDF structural ingestion.
Discovers all configs of type pdf_structural in /opt/airflow/configs/.
Flow: download PDF → write raw binary to bronze →
      parse tables by title pattern → write Parquet to bronze → stage to silver
"""
from airflow.decorators import dag, task

from ingestion.dags.factory import register_dags
from core.extractors.factory import get_extractor
from core.providers.factory import get_storage


def dag_factory(cfg: dict):
    @dag(
        dag_id=f"ingest_pdf_structural_{cfg['source_name']}",
        schedule=cfg.get("schedule", "@monthly"),
        catchup=False,
        tags=["ingestion", "pdf", "structural"],
    )
    def ingest():
        @task()
        def download_pdf() -> str:
            from storage import bronze
            pdf_bytes = get_extractor(cfg).extract()
            return bronze.write_bytes(pdf_bytes, cfg["source_name"], "source.pdf")

        @task()
        def parse_pdf(bronze_pdf_key: str) -> str:
            from storage import bronze
            from core.parsers.structural_parser import StructuralPdfParser
            pdf_bytes = bronze.read_bytes(bronze_pdf_key)
            df = StructuralPdfParser(cfg).parse(pdf_bytes)
            if df.empty:
                raise ValueError(f"StructuralPdfParser returned empty DataFrame for {cfg['source_name']}")
            return bronze.write_parquet(df, cfg["source_name"], "parsed.parquet")

        @task()
        def stage_silver(bronze_parquet_key: str):
            from storage import bronze, silver
            df = bronze.read_parquet(bronze_parquet_key)
            return silver.write(df, cfg["source_name"])

        stage_silver(parse_pdf(download_pdf()))

    return ingest()


register_dags("pdf_structural", dag_factory, globals())
