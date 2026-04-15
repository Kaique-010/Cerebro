from app.core.database import SessionLocal
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.embedding_service import EmbeddingService
from app.brain.memory_brain import MemoryBrain


class IngestService:
    def __init__(self):
        self.memory_brain = MemoryBrain()
        self.embedding_service = EmbeddingService()
        self.repository = KnowledgeRepository()

    def run(self) -> int:
        chunks = self.memory_brain.load_chunks()
        if not chunks:
            return 0

        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(texts)

        count = 0
        with SessionLocal() as db:
            for chunk, embedding in zip(chunks, embeddings):
                self.repository.upsert_chunk(db, chunk, embedding)
                count += 1

            db.commit()

        return count