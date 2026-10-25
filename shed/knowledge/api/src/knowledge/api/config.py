import os
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource

DomainName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]


def config_files(*names: str) -> list[Path]:
    directory = Path(os.environ.get("KNOWLEDGE_CONFIG_DIR", "/etc/knowledge"))
    return [directory / name for name in names]


class LoggingConfig(BaseModel):
    level: str


class ClickHouseConfig(BaseModel):
    host: str
    port: int
    database: Identifier
    user: str = Field(min_length=1)


class DomainTables(BaseModel):
    """A domain's two tables in the knowledge database, created and owned by the module that uses them."""

    documents: Identifier
    chunks: Identifier


class S3Config(BaseModel):
    endpoint: str
    region: str


class CollectionConfig(BaseModel):
    name: str = Field(min_length=1)
    tags: list[str] = Field(min_length=1)


class DomainConfig(BaseModel):
    """One domain's knowledge: its tables, its bucket, and the collections indexed from ``context/<collection>/knowledge/``."""

    tables: DomainTables
    bucket: str = Field(min_length=1)
    collections: list[CollectionConfig] = Field(min_length=1)

    def collection(self, name: str) -> CollectionConfig | None:
        return next((item for item in self.collections if item.name == name), None)


class RagConfig(BaseModel):
    embedding_model: str
    embedding_model_path: Path
    embedding_revision: str
    document_prefix: str
    query_prefix: str
    chunk_tokens: int = Field(gt=0)
    overlap_tokens: int = Field(ge=0)
    batch_size: int = Field(gt=0)
    candidate_results: int = Field(gt=0)
    max_context_tokens: int = Field(gt=0)
    max_results: int = Field(gt=0)
    index_interval_seconds: int = Field(gt=0)


class KnowledgeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=config_files("logging.yaml", "knowledge.yaml", "clickhouse.yaml", "s3.yaml"),
        env_prefix="KNOWLEDGE_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    logging: LoggingConfig
    rag: RagConfig
    domains: dict[DomainName, DomainConfig] = Field(min_length=1)
    clickhouse: ClickHouseConfig
    s3: S3Config
    clickhouse_password: SecretStr = Field(min_length=1, validation_alias="KNOWLEDGE_CLICKHOUSE_PASSWORD")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls, deep_merge=True),
            file_secret_settings,
        )


class S3Credentials(BaseSettings):
    """A domain's read credential for its bucket: ``KNOWLEDGE_<DOMAIN>_S3_ACCESS_KEY_ID`` and ``..._SECRET_ACCESS_KEY``."""

    model_config = SettingsConfigDict(extra="ignore")

    access_key_id: str = Field(min_length=1)
    secret_access_key: SecretStr = Field(min_length=1)

    @classmethod
    def for_domain(cls, domain: str) -> "S3Credentials":
        prefix = f"KNOWLEDGE_{domain.upper()}_S3_"
        return cls(_env_prefix=prefix)
