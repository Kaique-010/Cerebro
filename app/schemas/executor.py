from pydantic import BaseModel, Field
from typing import List


class ExecutorChunkRef(BaseModel):
    id: str
    brain: str
    title: str
    final_score: float


class AnswerBlock(BaseModel):
    text: str
    supports: List[str] = Field(default_factory=list)


class ExecutorResult(BaseModel):
    query: str
    answer_blocks: List[AnswerBlock] = Field(default_factory=list)
    final_answer: str
    used_chunks: List[ExecutorChunkRef] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    grounded: bool = True