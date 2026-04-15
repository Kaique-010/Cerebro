from app.core.database import SessionLocal
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.embedding_service import EmbeddingService
from app.services.reranker_service import RerankerService
from app.services.intent_service import IntentService
from app.services.context_builder import ContextBuilderService


class RetrievalBrain:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.repository = KnowledgeRepository()
        self.reranker = RerankerService()
        self.intent_service = IntentService()
        self.context_builder = ContextBuilderService()

    def search(
        self,
        query: str,
        top_k_vector: int = 10,
        top_k_final: int = 3,
        brains: list[str] | None = None
    ) -> dict:
        intent = self.intent_service.classify(query)
        query_embedding = self.embedding_service.embed_text(query)

        with SessionLocal() as db:
            candidates = self.repository.semantic_search(
                db=db,
                query_embedding=query_embedding,
                top_k=top_k_vector,
                brains=brains,
            )

        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k_vector,
        )

        context_result = self.context_builder.select(
            query=query,
            intent=intent,
            reranked_items=reranked,
            top_k_final=top_k_final,
        )

        return {
            "query": query,
            "intent": intent,
            "vector_candidates": candidates,
            "reranked_candidates": reranked,
            "context_result": context_result.model_dump(),
        }