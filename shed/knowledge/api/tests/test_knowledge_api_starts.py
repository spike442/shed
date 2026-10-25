import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock

CHART_CONFIG = Path(__file__).parents[4] / "infra" / "knowledge" / "chart" / "config"


def test_knowledge_api_starts_serving_and_indexing(monkeypatch, tmp_path) -> None:
    shutil.copy(CHART_CONFIG / "logging.yaml", tmp_path)
    shutil.copy(CHART_CONFIG / "knowledge.yaml", tmp_path)
    (tmp_path / "clickhouse.yaml").write_text(
        "clickhouse:\n  host: clickhouse.test\n  port: 8123\n  database: knowledge\n  user: knowledge\n"
    )
    (tmp_path / "s3.yaml").write_text("s3:\n  endpoint: http://s3.test\n  region: us-east-1\n")
    monkeypatch.setenv("KNOWLEDGE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("KNOWLEDGE_CLICKHOUSE_PASSWORD", "test")
    monkeypatch.setenv("KNOWLEDGE_SENTINEL_S3_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("KNOWLEDGE_SENTINEL_S3_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("KNOWLEDGE_RAG__EMBEDDING_REVISION", "test")
    from knowledge.api import main

    server = Mock(serve=AsyncMock())
    indexer = Mock(index_documents=Mock(return_value=0))
    for name in ("ClickHouse", "Embeddings", "RagRetriever", "s3_client"):
        monkeypatch.setattr(main, name, Mock())
    monkeypatch.setattr(main, "DomainIndexer", Mock(return_value=indexer))
    monkeypatch.setattr(main, "Server", Mock(return_value=server))

    main.main()

    server.serve.assert_awaited_once()
    indexer.index_documents.assert_called()
