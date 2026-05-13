"""
Airflow DAG: exec_kpi_pipeline
Orchestrates the daily refresh of the executive KPI dashboard.

Stages:
    1. Extract  – pull source CSV/Parquet from object storage to raw schema
    2. Freshness – dbt source freshness check (fail fast if data is stale)
    3. Transform – dbt run staging -> core -> kpi
    4. Test      – dbt tests (uniqueness, not_null, relationships, accepted_values)
    5. Refresh   – trigger Power BI / Tableau dataset refresh via REST API
    6. Notify    – post pipeline status to #data-alerts on Slack
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

default_args = {
    "owner": "data-platform",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

DBT_DIR = "/opt/airflow/dbt_project"
DBT_CMD = f"cd {DBT_DIR} && dbt"


def refresh_bi_dataset(**context):
    """Trigger downstream BI tool dataset refresh (Power BI / Tableau)."""
    import os
    import requests

    workspace_id = os.environ["PBI_WORKSPACE_ID"]
    dataset_id = os.environ["PBI_DATASET_ID"]
    token = os.environ["PBI_ACCESS_TOKEN"]

    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        f"/datasets/{dataset_id}/refreshes"
    )
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    return resp.status_code


with DAG(
    dag_id="exec_kpi_pipeline",
    default_args=default_args,
    description="Daily refresh of the executive KPI dashboard.",
    schedule_interval="0 6 * * *",          # 06:00 UTC every day
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["analytics", "executive", "kpi"],
) as dag:

    extract = BashOperator(
        task_id="extract_sources",
        bash_command=(
            "python /opt/airflow/scripts/extract_sources.py "
            "--date {{ ds }} --target s3://data-lake/raw/"
        ),
    )

    freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{DBT_CMD} source freshness --profiles-dir {DBT_DIR}",
    )

    run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"{DBT_CMD} run --select staging --profiles-dir {DBT_DIR}",
    )

    run_core = BashOperator(
        task_id="dbt_run_core",
        bash_command=f"{DBT_CMD} run --select marts.core --profiles-dir {DBT_DIR}",
    )

    run_kpi = BashOperator(
        task_id="dbt_run_kpi",
        bash_command=f"{DBT_CMD} run --select marts.kpi --profiles-dir {DBT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{DBT_CMD} test --profiles-dir {DBT_DIR}",
    )

    refresh = PythonOperator(
        task_id="refresh_powerbi_dataset",
        python_callable=refresh_bi_dataset,
    )

    notify = SlackWebhookOperator(
        task_id="slack_success_notification",
        http_conn_id="slack_webhook",
        message=(
            ":white_check_mark: *Executive KPI dashboard refreshed.*\n"
            "Run: `{{ ds }}` | Duration: {{ macros.datetime.utcnow() }}"
        ),
        channel="#data-alerts",
    )

    extract >> freshness >> run_staging >> run_core >> run_kpi >> dbt_test >> refresh >> notify
