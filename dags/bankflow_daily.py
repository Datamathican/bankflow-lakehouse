"""Airflow DAG: daily orchestration of the BankFlow pipeline.

Each stage is an idempotent CLI call, so the same commands run in Airflow,
cron, CI or a laptop. dbt build runs models *and* tests, so a failed data
quality test stops the DAG before anything is exported.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="bankflow_daily",
    description="Bronze -> Silver -> Gold banking pipeline with fraud signals",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["banking", "lakehouse", "fraud"],
) as dag:
    generate = BashOperator(task_id="land_raw_extracts", bash_command="bankflow generate")
    ingest = BashOperator(task_id="bronze_ingest_with_contracts", bash_command="bankflow ingest")
    transform = BashOperator(task_id="dbt_silver_gold_and_tests", bash_command="bankflow transform")
    export = BashOperator(task_id="export_gold_parquet", bash_command="bankflow export")
    report = BashOperator(task_id="reconciliation_and_fraud_report", bash_command="bankflow report")

    generate >> ingest >> transform >> export >> report
