from pydantic import BaseModel, Field
from typing import List, Dict, Any


class KnowledgeChunk(BaseModel):
    id: str = Field(description="Identitificador de chunk de conhecimento")
    brain: str = Field(description="Identitificador de brain")
    type: str = Field(description="Tipo de chunk de conhecimento")
    title: str = Field(description="Título do chunk de conhecimento")
    content: str = Field(description="Conteúdo do chunk de conhecimento")
    tags: List[str] = Field(default_factory=list)
    priority: int = 5
    source: str = "manual"
    version: str = "1.0.0"
    related_entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)


class ChunkMetadata(BaseModel):
    file_name: str
    section_title: str
    chunk_index: int
    total_chunks_in_file: int
    char_count: int