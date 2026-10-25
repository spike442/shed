from datetime import datetime, timedelta
from pathlib import Path

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from airflow.sdk import Param

TIMEZONE = "Europe/Paris"
START_DATE = datetime(2026, 10, 1)
NAMESPACE = "{{ var.value.get('stonks_namespace', 'agents') }}"
REGISTRY = "{{ var.value.get('stonks_registry', 'ghcr.io/spike442/shed') }}"
VERSION = "{{ var.value.stonks_version }}"
TRADE_DATE = (
    "{{ params.trade_date or (logical_date or dag_run.run_after).in_timezone('"
    + TIMEZONE
    + "').strftime('%Y-%m-%d') }}"
)
SECRET = "stonks-secrets"
S3_KEYS = ("S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
TEMPLATES = Path(__file__).parent / "templates"
POD_TEMPLATE = str(TEMPLATES / "stonks-pod.yaml")

PARAMS = {
    "trade_date": Param(
        "",
        type="string",
        description="Trade date as YYYY-MM-DD; empty uses the run's date in Europe/Paris.",
    )
}
DEFAULT_ARGS = {
    "owner": "stonks",
    "retries": 0,
    "retry_delay": timedelta(minutes=10),
}


def secret_env(keys: tuple[str, ...]) -> list[Secret]:
    return [Secret("env", key, SECRET, key) for key in keys]


def stonks_pod(task_id: str, module: str, *, secrets: tuple[str, ...], **kwargs) -> KubernetesPodOperator:
    secret_keys = secret_env(secrets)
    return KubernetesPodOperator(
        task_id=task_id,
        name=f"stonks-{module}-{task_id}",
        namespace=NAMESPACE,
        pod_template_file=POD_TEMPLATE,
        image=f"{REGISTRY}/stonks-{module}:{VERSION}",
        arguments=[task_id, "--trade-date", TRADE_DATE],
        secrets=secret_keys,
        labels={"app.kubernetes.io/name": f"stonks-{module}"},
        termination_message_policy="FallbackToLogsOnError",
        get_logs=True,
        log_events_on_failure=True,
        log_pod_spec_on_failure=False,
        on_finish_action="delete_pod",
        startup_timeout_seconds=600,
        **kwargs,
    )


def stonks_spark(task_id: str, **kwargs) -> SparkKubernetesOperator:
    return SparkKubernetesOperator(
        task_id=task_id,
        namespace=NAMESPACE,
        application_file="templates/stonks-spark.yaml",
        get_logs=True,
        delete_on_termination=True,
        **kwargs,
    )
