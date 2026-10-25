DROP TABLE IF EXISTS knowledge.sentinel_documents;

CREATE TABLE IF NOT EXISTS knowledge.sentinel_documents (
    source_id String,
    generation UUID,
    object_key String,
    tags Array(String),
    collection LowCardinality(String),
    source_revision String,
    content_hash String,
    index_signature String,
    content String,
    version UInt64,
    is_deleted UInt8,
    indexed_at DateTime64(6, 'UTC')
) ENGINE = ReplacingMergeTree(version)
ORDER BY source_id;

DROP TABLE IF EXISTS knowledge.sentinel_chunks;

CREATE TABLE IF NOT EXISTS knowledge.sentinel_chunks (
    source_id String,
    generation UUID,
    chunk_number UInt32,
    object_key String,
    content String,
    embedding Array(Float32),
    CONSTRAINT embedding_dimensions CHECK length(embedding) = 768,
    INDEX embedding_hnsw embedding TYPE vector_similarity('hnsw', 'cosineDistance', 768)
) ENGINE = MergeTree
ORDER BY (source_id, generation, chunk_number);
