from dataclasses import dataclass, field
from importlib.metadata import version
from threading import Event

from knowledge.api.config import DomainConfig, RagConfig
from knowledge.api.documents import KnowledgeDocument
from knowledge.api.embeddings import Embeddings
from knowledge.api.index_store import KnowledgeIndexStore, is_unchanged
from knowledge.api.s3 import S3KnowledgeSource
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shed.core.digest import json_digest, text_digest


class DomainIndexer:
    """Indexes one domain's collections from its bucket into its tables in the knowledge database."""

    def __init__(
        self, rag: RagConfig, domain: DomainConfig, store: KnowledgeIndexStore, embeddings: Embeddings, s3_client
    ):
        self.domain = domain
        self.store = store
        self.embeddings = embeddings
        self.s3_client = s3_client
        self.signature = json_digest(
            {
                "backend": version("fastembed"),
                "model": rag.embedding_model,
                "revision": rag.embedding_revision,
                "chunk_tokens": rag.chunk_tokens,
                "overlap_tokens": rag.overlap_tokens,
                "document_prefix": rag.document_prefix,
                "query_prefix": rag.query_prefix,
            }
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=rag.chunk_tokens,
            chunk_overlap=rag.overlap_tokens,
            length_function=self.embeddings.count_tokens,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
        )

    def source_documents(self):
        for collection in self.domain.collections:
            source = S3KnowledgeSource(self.s3_client, self.domain.bucket, collection.name)
            objects = source.list_objects()
            for key, revision in objects:
                content = source.read_object(key)
                yield KnowledgeDocument(
                    key=key,
                    tags=collection.tags,
                    collection=collection.name,
                    revision=revision,
                    content=content,
                )

    def index_documents(self) -> int:
        indexed = 0
        keys = set()
        current = self.store.indexed_documents()
        documents = self.source_documents()
        for document in documents:
            keys.add(document.key)
            checksum = text_digest(document.content)
            source_id = text_digest(document.key)
            indexed_state = current.get(source_id)
            if is_unchanged(indexed_state, document, checksum, self.signature):
                continue
            chunks = self.splitter.split_text(document.content)
            vectors = self.embeddings.embed_documents(chunks)
            self.store.replace_document(document, checksum, self.signature, chunks, vectors)
            indexed += 1
        retired = self.store.retire_missing(keys)
        if indexed or retired:
            self.store.prune_chunks()
        return indexed


@dataclass(frozen=True)
class DomainIndex:
    """One domain's configuration, store, and indexer, with whether a pass was attempted and one succeeded."""

    config: DomainConfig
    store: KnowledgeIndexStore
    indexer: DomainIndexer
    attempted: Event = field(default_factory=Event)
    indexed: Event = field(default_factory=Event)
