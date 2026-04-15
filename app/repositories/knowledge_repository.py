import json
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.chunker import KnowledgeChunk


class KnowledgeRepository:
    def upsert_chunk(
        self,
        db: Session,
        chunk: KnowledgeChunk,
        embedding: list[float]
    ) -> None:
        sql = text("""
            INSERT INTO knowledge_chunks (
                id, brain, type, title, content, tags, priority,
                source, version, related_entities, metadata, embedding
            )
            VALUES (
                :id, :brain, :type, :title, :content, :tags, :priority,
                :source, :version, :related_entities, :metadata, :embedding
            )
            ON CONFLICT (id) DO UPDATE SET
                brain = EXCLUDED.brain,
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                tags = EXCLUDED.tags,
                priority = EXCLUDED.priority,
                source = EXCLUDED.source,
                version = EXCLUDED.version,
                related_entities = EXCLUDED.related_entities,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
        """)

        db.execute(
            sql,
            {
                "id": chunk.id,
                "brain": chunk.brain,
                "type": chunk.type,
                "title": chunk.title,
                "content": chunk.content,
                "tags": json.dumps(chunk.tags, ensure_ascii=False),
                "priority": chunk.priority,
                "source": chunk.source,
                "version": chunk.version,
                "related_entities": json.dumps(chunk.related_entities, ensure_ascii=False),
                "metadata": json.dumps(chunk.metadata, ensure_ascii=False),
                "embedding": embedding,
            }
        )

    def semantic_search(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int = 10,
        brains: list[str] | None = None
    ) -> list[dict]:
        base_sql = """
            SELECT
                id,
                brain,
                type,
                title,
                content,
                tags,
                priority,
                source,
                version,
                related_entities,
                metadata,
                1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM knowledge_chunks
        """

        params = {
            "embedding": str(query_embedding),
            "top_k": top_k,
        }

        filters = []
        if brains:
            filters.append("brain = ANY(:brains)")
            params["brains"] = brains

        if filters:
            base_sql += " WHERE " + " AND ".join(filters)

        base_sql += """
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """

        rows = db.execute(text(base_sql), params).mappings().all()
        return [dict(row) for row in rows]