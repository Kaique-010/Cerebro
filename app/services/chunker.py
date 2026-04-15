import re
from pathlib import Path
from typing import List

from app.schemas.chunker import KnowledgeChunk


class ChunkerService:
    def split_markdown_sections(self, content: str) -> List[tuple[str, str]]:
        """
        Divide o markdown por títulos (#, ##, ###).
        Retorna lista de tuplas: (titulo_da_secao, conteudo_da_secao)
        """
        lines = content.splitlines()
        sections = []

        current_title = "Conteúdo Geral"
        current_content = []

        heading_pattern = re.compile(r"^(#{1,3})\s+(.*)$")

        for line in lines:
            match = heading_pattern.match(line.strip())

            if match:
                if current_content:
                    sections.append(
                        (current_title, "\n".join(current_content).strip())
                    )
                    current_content = []

                current_title = match.group(2).strip()
            else:
                current_content.append(line)

        if current_content:
            sections.append(
                (current_title, "\n".join(current_content).strip())
            )

        return [(title, content) for title, content in sections if content.strip()]

    def split_large_text(self, text: str, max_chars: int = 500) -> List[str]:
        """
        Divide textos grandes em blocos menores por parágrafo.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""

        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= max_chars:
                current = f"{current}\n\n{paragraph}".strip()
            else:
                if current:
                    chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)

        return chunks

    def file_to_chunks(self, file_path: Path) -> List[KnowledgeChunk]:
        brain = file_path.parent.name
        raw_content = file_path.read_text(encoding="utf-8").strip()
        sections = self.split_markdown_sections(raw_content)

        chunks: List[KnowledgeChunk] = []
        chunk_counter = 1

        for section_title, section_content in sections:
            text_parts = self.split_large_text(section_content, max_chars=500)

            for part in text_parts:
                chunk_id = f"{file_path.stem}_{chunk_counter}"

                chunk = KnowledgeChunk(
                    id=chunk_id,
                    brain=brain,
                    type="secao_markdown",
                    title=section_title,
                    content=part,
                    tags=[brain, file_path.stem],
                    source=str(file_path),
                    metadata={
                        "file_name": file_path.name,
                        "section_title": section_title,
                        "chunk_index": chunk_counter,
                        "char_count": len(part),
                    },
                )

                chunks.append(chunk)
                chunk_counter += 1

        total_chunks = len(chunks)

        for chunk in chunks:
            chunk.metadata["total_chunks_in_file"] = total_chunks

        return chunks