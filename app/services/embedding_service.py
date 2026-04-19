from openai import OpenAI
from app.core.config import settings
from app.core.logging import get_logger


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.logger = get_logger("service.embedding")
    
    def embed_text(self, text: str) -> list[float]:
        self.logger.info(
            "Gerando embedding | model=%s | chars=%s",
            self.model,
            len(text or ""),
        )
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        self.logger.info("Embedding concluído")
        return response.data[0].embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
