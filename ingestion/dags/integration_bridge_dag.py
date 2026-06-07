"""
DAG: Integration Bridge — triggered manually or on a sensor.
Reads two silver table names from dag_run.conf and runs IntegrationAgent.
Expected conf: {"table_a": "silver_name_a", "table_b": "silver_name_b"}
"""
import sys

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

sys.path.insert(0, "/opt/airflow")


@dag(
    dag_id="integration_bridge",
    schedule=None,  # triggered manually or by external sensor
    start_date=days_ago(1),
    catchup=False,
    tags=["integration", "bridge"],
)
def integration_bridge_dag():
    @task()
    def run_integration(**context):
        conf = context["dag_run"].conf or {}
        table_a = conf.get("table_a")
        table_b = conf.get("table_b")

        if not table_a or not table_b:
            raise ValueError(
                "dag_run.conf must contain 'table_a' and 'table_b'. "
                f"Received: {conf}"
            )

        from bridge.integration_bridge import run_integration as _run
        out_path = _run(table_a, table_b)
        return str(out_path)

    run_integration()


integration_bridge_dag()
