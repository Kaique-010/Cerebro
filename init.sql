CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id TEXT PRIMARY KEY,
    brain TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    priority INTEGER NOT NULL DEFAULT 5,
    source TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    related_entities JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1536)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_brain
ON knowledge_chunks (brain);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_tags
ON knowledge_chunks
USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_metadata
ON knowledge_chunks
USING GIN (metadata);