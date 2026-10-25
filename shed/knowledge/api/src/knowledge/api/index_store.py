from datetime import UTC, datetime
from time import time_ns
from uuid import uuid4

from knowledge.api.clickhouse import ClickHouse
from knowledge.api.config import DomainTables
from knowledge.api.documents import KnowledgeDocument
from shed.core.digest import text_digest


def is_unchanged(indexed: dict | None, document: KnowledgeDocument, checksum: str, signature: str) -> bool:
    return indexed == {
        "source_revision": document.revision,
        "content_hash": checksum,
        "index_signature": signature,
        "tags": document.tags,
        "collection": document.collection,
    }


class KnowledgeIndexStore:
    """One domain's knowledge tables, named by its configuration and owned by its module."""

    def __init__(self, database: ClickHouse, tables: DomainTables):
        self.database = database
        self.documents = tables.documents
        self.chunks = tables.chunks
        self.live_documents = f"{tables.documents} FINAL WHERE NOT is_deleted"

    def indexed_documents(self) -> dict[str, dict]:
        rows = self.database.query(
            "SELECT source_id, source_revision, content_hash, index_signature, tags, collection "
            f"FROM {self.live_documents}"
        )
        return {row.pop("source_id"): row for row in rows}

    def replace_document(
        self,
        document: KnowledgeDocument,
        checksum: str,
        signature: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        source_id = text_digest(document.key)
        generation = uuid4()
        pairs = zip(chunks, embeddings, strict=True)
        chunk_rows = [
            [source_id, generation, number, document.key, content, vector]
            for number, (content, vector) in enumerate(pairs)
        ]
        chunk_columns = ["source_id", "generation", "chunk_number", "object_key", "content", "embedding"]
        self.database.insert(self.chunks, chunk_rows, chunk_columns)
        self.database.insert(
            self.documents,
            [
                [
                    source_id,
                    generation,
                    document.key,
                    document.tags,
                    document.collection,
                    document.revision,
                    checksum,
                    signature,
                    document.content,
                    time_ns(),
                    0,
                    datetime.now(UTC),
                ]
            ],
            [
                "source_id",
                "generation",
                "object_key",
                "tags",
                "collection",
                "source_revision",
                "content_hash",
                "index_signature",
                "content",
                "version",
                "is_deleted",
                "indexed_at",
            ],
        )

    def retire_missing(self, keys: set[str]) -> int:
        active_ids = {text_digest(key) for key in keys}
        rows = self.database.query(f"SELECT * FROM {self.live_documents}")
        retired = 0
        for row in rows:
            if row["source_id"] in active_ids:
                continue
            version = time_ns()
            indexed_at = datetime.now(UTC)
            row.update(version=version, is_deleted=1, indexed_at=indexed_at)
            columns = list(row)
            values = [row[column] for column in columns]
            self.database.insert(self.documents, [values], columns)
            retired += 1
        return retired

    def prune_chunks(self) -> None:
        self.database.command(
            f"ALTER TABLE {self.chunks} DELETE WHERE (source_id, generation) NOT IN "
            f"(SELECT source_id, generation FROM {self.live_documents})"
        )

    def search_chunks(self, collection: str, tag: str, embedding: list[float], candidates: int) -> list[dict]:
        rows = self.database.query(
            "SELECT source_id, toString(generation) AS generation, chunk_number, object_key, content, "
            f"1 - cosineDistance(embedding, {{embedding:Array(Float32)}}) AS score FROM {self.chunks} "
            f"WHERE (source_id, generation) IN (SELECT source_id, generation FROM {self.live_documents} "
            "AND has(tags, {tag:String}) AND collection = {collection:String}) "
            "ORDER BY cosineDistance(embedding, {embedding:Array(Float32)}) ASC, source_id, chunk_number "
            "LIMIT {limit:UInt32}",
            {"tag": tag, "collection": collection, "embedding": embedding, "limit": candidates},
        )
        return [{**row, "source": f"{row['object_key']}#chunk-{row['chunk_number']}"} for row in rows]
