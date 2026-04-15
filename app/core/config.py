import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_RERANK_MODEL = os.getenv("OPENAI_RERANK_MODEL", "gpt-5.4-mini")
    OPENAI_EXECUTOR_MODEL = os.getenv("OPENAI_EXECUTOR_MODEL", "gpt-5.4-mini")

    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "brain")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "brain_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "brain_pass")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()