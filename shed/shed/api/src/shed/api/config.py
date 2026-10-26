import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict
from sentinel.core.config.common import CommonSettings
from sentinel.core.contracts.reviews import RepositoryConfig


def config_files(*names: str) -> list[Path]:
    directory = Path(os.environ.get("SHED_CONFIG_DIR", "/etc/shed"))
    return [directory / name for name in names]


class ApiSettings(CommonSettings):
    model_config = SettingsConfigDict(
        yaml_file=config_files(
            "logging.yaml",
            "agents.yaml",
            "repositories.yaml",
            "kafka.yaml",
            "database.yaml",
        ),
        env_prefix="SHED_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    repositories: list[RepositoryConfig]
    kafka_username: str = Field(min_length=1, validation_alias="SHED_KAFKA_USERNAME")
    kafka_password: SecretStr = Field(min_length=1, validation_alias="SHED_KAFKA_PASSWORD")
    database_password: SecretStr = Field(min_length=1, validation_alias="SHED_DATABASE_PASSWORD")
