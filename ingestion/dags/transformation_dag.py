"""
DAG: dbt transformation — roda os modelos bronze/silver/gold do gov_hub.

O projeto dbt vive em gov-hub/transformation/ (montado em /opt/airflow/transformation
no container). É completamente independente do Airflow: pode ser rodado via CLI
fora do container com `dbt run --project-dir transformation/`.

Dispara diariamente após a janela de ingestão (01:00).
"""
import os
from datetime import datetime
from pathlib import Path

from cosmos import DbtDag, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.constants import DBT_LOG_PATH_ENVVAR

DBT_LOG_PATH = "/tmp/dbt_logs"
os.makedirs(DBT_LOG_PATH, exist_ok=True)
os.environ[DBT_LOG_PATH_ENVVAR] = DBT_LOG_PATH

# transformation/ é montado como volume separado — independente de dags/
TRANSFORMATION_DIR = Path("/opt/airflow/transformation")

profile_config = ProfileConfig(
    profiles_yml_filepath=TRANSFORMATION_DIR / "profiles.yml",
    profile_name="gov_hub",
    target_name="prod",
)

transformation_dag = DbtDag(
    project_config=ProjectConfig(TRANSFORMATION_DIR),
    profile_config=profile_config,
    execution_config=ExecutionConfig(
        dbt_executable_path="dbt",
    ),
    schedule_interval="0 1 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    dag_id="gov_hub_transformation",
    default_args={"retries": 2},
    tags=["transformation", "dbt"],
)
