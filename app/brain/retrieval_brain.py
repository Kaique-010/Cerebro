from app.core.database import SessionLocal
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.embedding_service import EmbeddingService
from app.services.reranker_service import RerankerService
from app.services.intent_service import IntentService
from app.services.context_builder import ContextBuilderService
from app.core.logging import get_logger


class RetrievalBrain:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.repository = KnowledgeRepository()
        self.reranker = RerankerService()
        self.intent_service = IntentService()
        self.context_builder = ContextBuilderService()
        self.logger = get_logger("brain.retrieval")

    def search(
        self,
        query: str,
        top_k_vector: int = 10,
        top_k_final: int = 3,
        brains: list[str] | None = None
    ) -> dict:
        intent = self.intent_service.classify(query)
        self.logger.info(
            "Busca iniciada | query=%s | intent=%s | top_k_vector=%s | top_k_final=%s | brains=%s",
            query[:200],
            intent,
            top_k_vector,
            top_k_final,
            brains,
        )

        self.logger.info("Etapa retrieval: gerando embedding")
        query_embedding = self.embedding_service.embed_text(query)
        self.logger.info("Etapa retrieval: embedding concluído")

        self.logger.info("Etapa retrieval: semantic search")
        with SessionLocal() as db:
            candidates = self.repository.semantic_search(
                db=db,
                query_embedding=query_embedding,
                top_k=top_k_vector,
                brains=brains,
            )
        self.logger.info("Etapa retrieval: semantic search concluída | candidates=%s", len(candidates))

        self.logger.info("Etapa retrieval: rerank")
        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k_vector,
        )
        self.logger.info("Etapa retrieval: rerank concluído | reranked=%s", len(reranked))

        context_result = self.context_builder.select(
            query=query,
            intent=intent,
            reranked_items=reranked,
            top_k_final=top_k_final,
        )

        selected_chunks = context_result.selected_chunks
        self.logger.info(
            "Busca concluída | vector_candidates=%s | reranked=%s | selected=%s",
            len(candidates),
            len(reranked),
            len(selected_chunks),
        )
        for chunk in selected_chunks:
            source = chunk.metadata.get("file_name", "desconhecido")
            self.logger.info(
                "Chunk selecionado | id=%s | brain=%s | title=%s | score=%s | source=%s",
                chunk.id,
                chunk.brain,
                chunk.title,
                chunk.final_score,
                source,
            )

        return {
            "query": query,
            "intent": intent,
            "vector_candidates": candidates,
            "reranked_candidates": reranked,
            "context_result": context_result.model_dump(),
        }
