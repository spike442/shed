import asyncio
import logging
import threading
from collections.abc import Mapping
from contextlib import ExitStack

from knowledge.api.clickhouse import ClickHouse
from knowledge.api.config import KnowledgeSettings, S3Credentials
from knowledge.api.embeddings import Embeddings
from knowledge.api.index_store import KnowledgeIndexStore
from knowledge.api.indexer import DomainIndex, DomainIndexer
from knowledge.api.retriever import RagRetriever
from knowledge.api.s3 import s3_client
from knowledge.api.server import create_app
from uvicorn import Config, Server

logger = logging.getLogger(__name__)

SEARCH_PORT = 9092


def index_periodically(domains: Mapping[str, DomainIndex], interval: int, stopped: threading.Event) -> None:
    """Index every domain on startup and periodically, retrying a failed domain within a minute.

    A domain is searchable after its first successful pass and stays searchable: a later failed pass keeps
    serving the index it already has, and one domain's failure never stops the others.
    """
    while not stopped.is_set():
        delay = interval
        for name, domain in domains.items():
            try:
                count = domain.indexer.index_documents()
                domain.indexed.set()
                logger.info("Knowledge indexing complete domain=%s changed_documents=%s", name, count)
            except Exception:
                delay = min(interval, 60)
                logger.exception("Knowledge indexing failed domain=%s", name)
            finally:
                domain.attempted.set()
        stopped.wait(delay)


def build_domains(
    settings: KnowledgeSettings, clickhouse: ClickHouse, embeddings: Embeddings, resources: ExitStack
) -> dict[str, DomainIndex]:
    domains = {}
    for name, config in settings.domains.items():
        credentials = S3Credentials.for_domain(name)
        bucket_client = s3_client(settings.s3, credentials)
        resources.callback(bucket_client.close)
        store = KnowledgeIndexStore(clickhouse, config.tables)
        indexer = DomainIndexer(settings.rag, config, store, embeddings, bucket_client)
        domains[name] = DomainIndex(config=config, store=store, indexer=indexer)
    return domains


async def serve_knowledge(settings: KnowledgeSettings) -> None:
    embeddings = Embeddings(settings.rag)
    retriever = RagRetriever(settings.rag, embeddings)
    stopped = threading.Event()
    with ExitStack() as resources:
        clickhouse = ClickHouse(settings.clickhouse, settings.clickhouse_password)
        resources.callback(clickhouse.close)
        domains = build_domains(settings, clickhouse, embeddings, resources)
        indexing = threading.Thread(
            target=index_periodically,
            args=(domains, settings.rag.index_interval_seconds, stopped),
            name="knowledge-index",
            daemon=True,
        )
        indexing.start()
        app = create_app(domains, retriever, clickhouse)
        config = Config(app, host="0.0.0.0", port=SEARCH_PORT)
        server = Server(config)
        try:
            await server.serve()
        finally:
            stopped.set()
            indexing.join(timeout=10)


def main() -> None:
    settings = KnowledgeSettings()
    level = settings.logging.level.upper()
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s", force=True)
    service = serve_knowledge(settings)
    asyncio.run(service)


if __name__ == "__main__":
    main()
