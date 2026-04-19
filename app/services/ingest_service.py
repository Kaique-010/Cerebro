from app.core.database import SessionLocal
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.embedding_service import EmbeddingService
from app.brain.memory_brain import MemoryBrain
from app.core.logging import get_logger


class IngestService:
    def __init__(self):
        self.memory_brain = MemoryBrain()
        self.embedding_service = EmbeddingService()
        self.repository = KnowledgeRepository()
        self.logger = get_logger("ingest.service")

    def run(self) -> int:
        chunks = self.memory_brain.load_chunks()
        if not chunks:
            self.logger.info("Nenhum chunk encontrado para ingestão.")
            return 0

        self.logger.info("Chunks carregados | total_chunks=%s", len(chunks))
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(texts)
        self.logger.info("Embeddings gerados | total_embeddings=%s", len(embeddings))

        count = 0
        with SessionLocal() as db:
            for chunk, embedding in zip(chunks, embeddings):
                self.repository.upsert_chunk(db, chunk, embedding)
                count += 1

            db.commit()

        self.logger.info("Ingestão finalizada | chunks_persistidos=%s", count)
        return count
