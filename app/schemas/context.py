from pydantic import BaseModel, Field
from typing import List, Dict, Any


class ScoredChunk(BaseModel):
    id: str
    brain: str
    title: str
    content: str
    vector_score: float
    rerank_score: float
    final_score: float
    priority: int = 5
    tags: List[str] = Field(default_factory=list)
    source: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    selection_reason: str = ""


class DiscardedChunk(BaseModel):
    id: str
    reason: str


class ContextBuildResult(BaseModel):
    query: str
    intent: str
    selected_chunks: List[ScoredChunk] = Field(default_factory=list)
    discarded_chunks: List[DiscardedChunk] = Field(default_factory=list)
    context_text: str = ""