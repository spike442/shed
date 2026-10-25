from datetime import timedelta

import pendulum
from airflow.sdk import DAG
from airflow.timetables.trigger import CronTriggerTimetable
from kubernetes.client import models as k8s
from stonks_pods import DEFAULT_ARGS, PARAMS, S3_KEYS, START_DATE, TIMEZONE, stonks_pod

PAGE_READER_RESOURCES = k8s.V1ResourceRequirements(
    requests={"cpu": "100m", "memory": "512Mi"},
    limits={"memory": "2Gi"},
)

with DAG(
    dag_id="stonks_dividends",
    description="Dividend agent research, then validation into the dividend dates reference.",
    schedule=CronTriggerTimetable("30 19 * * 1-5", timezone=TIMEZONE),
    start_date=pendulum.instance(START_DATE, tz=TIMEZONE),
    catchup=False,
    max_active_runs=1,
    params=PARAMS,
    default_args=DEFAULT_ARGS,
    tags=["stonks", "dividends"],
):
    research = stonks_pod(
        "research",
        "dividends",
        secrets=(*S3_KEYS, "LLM_API_KEY"),
        container_resources=PAGE_READER_RESOURCES,
        retries=1,
        retry_delay=timedelta(minutes=20),
        execution_timeout=timedelta(hours=2, minutes=30),
    )
    validate = stonks_pod(
        "validate",
        "dividends",
        secrets=S3_KEYS,
        container_resources=PAGE_READER_RESOURCES,
        retries=2,
        retry_delay=timedelta(minutes=10),
        execution_timeout=timedelta(minutes=30),
    )
    research >> validate
