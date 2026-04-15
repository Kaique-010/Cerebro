from openai import OpenAI
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY )
        self.model = settings.OPENAI_EMBEDDING_MODEL
    
    def embed_text(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
