from collections.abc import Mapping

from fastapi import FastAPI, HTTPException
from knowledge.api.clickhouse import ClickHouse
from knowledge.api.indexer import DomainIndex
from knowledge.api.retriever import RagRetriever
from knowledge.client.contracts import (
    KnowledgeCollection,
    KnowledgeDomain,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)


def domain_summary(name: str, domain: DomainIndex) -> KnowledgeDomain:
    collections = [KnowledgeCollection(name=item.name, tags=item.tags) for item in domain.config.collections]
    indexed = domain.indexed.is_set()
    return KnowledgeDomain(name=name, collections=collections, indexed=indexed)


def create_app(domains: Mapping[str, DomainIndex], retriever: RagRetriever, clickhouse: ClickHouse) -> FastAPI:
    app = FastAPI(title="Shed knowledge", version="1", docs_url=None, redoc_url=None)

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def ready() -> dict[str, str]:
        pending = [name for name, domain in domains.items() if not domain.attempted.is_set()]
        if pending:
            raise HTTPException(status_code=503, detail=f"First indexing pass pending: {', '.join(pending)}")
        clickhouse.query("SELECT 1")
        return {"status": "ready"}

    @app.get("/v1/domains", response_model=list[KnowledgeDomain])
    def list_domains() -> list[KnowledgeDomain]:
        return [domain_summary(name, domain) for name, domain in domains.items()]

    @app.post("/v1/domains/{domain}/search", response_model=KnowledgeSearchResponse)
    def search(domain: str, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        index = domains.get(domain)
        if index is None:
            raise HTTPException(status_code=404, detail=f"Unknown knowledge domain: {domain}")
        collection = index.config.collection(request.collection)
        if collection is None:
            raise HTTPException(status_code=404, detail=f"Unknown {domain} collection: {request.collection}")
        if not index.indexed.is_set():
            raise HTTPException(status_code=503, detail=f"The {domain} knowledge is not indexed yet")
        results = retriever.retrieve_context(index.store, request.collection, request.tag, request.query)
        return KnowledgeSearchResponse(results=results)

    return app
