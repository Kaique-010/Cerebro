import json
from pathlib import Path

from app.services.chunker import ChunkerService
from app.schemas.chunker import KnowledgeChunk


class MemoryBrain:
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.chunker = ChunkerService()

    def load_chunks(self) -> list[KnowledgeChunk]:
        all_chunks: list[KnowledgeChunk] = []

        for file_path in self.knowledge_dir.rglob("*.md"):
            file_chunks = self.chunker.file_to_chunks(file_path)
            all_chunks.extend(file_chunks)

        return all_chunks

    def export_chunks(self, output_file: str = "data/chunks.json") -> list[KnowledgeChunk]:
        chunks = self.load_chunks()

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(
            json.dumps(
                [chunk.model_dump() for chunk in chunks],
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        return chunks