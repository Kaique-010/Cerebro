import re
from pathlib import Path
from typing import List

from app.schemas.chunker import KnowledgeChunk
from app.services.curated_parser import CuratedParserService


class ChunkerService:
    def __init__(self):
        self.curated_parser = CuratedParserService()

    def split_markdown_sections(self, content: str) -> List[tuple[str, str]]:
        lines = content.splitlines()
        sections = []

        current_title = "Conteúdo Geral"
        current_content = []

        heading_pattern = re.compile(r"^(#{1,3})\s+(.*)$")

        for line in lines:
            match = heading_pattern.match(line.strip())

            if match:
                if current_content:
                    sections.append((current_title, "\n".join(current_content).strip()))
                    current_content = []

                current_title = match.group(2).strip()
            else:
                current_content.append(line)

        if current_content:
            sections.append((current_title, "\n".join(current_content).strip()))

        return [(title, content) for title, content in sections if content.strip()]

    def split_large_text(self, text: str, max_chars: int = 900) -> List[str]:
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

    def build_tags(self, brain: str, file_stem: str, content: str, extra_tags: list[str] | None = None) -> list[str]:
        base_tags = {brain, file_stem}
        if extra_tags:
            base_tags.update(extra_tags)

        known_terms = [
            "django", "drf", "service", "serializer", "view", "cbv",
            "slug", "db_alias", "empresa", "filial", "tenant",
            "multi-tenant", "react native", "form", "api", "web",
        ]

        lower_content = content.lower()
        for term in known_terms:
            if term.lower() in lower_content:
                base_tags.add(term)

        return sorted(base_tags)

    def file_to_chunks(self, file_path: Path) -> List[KnowledgeChunk]:
        brain = file_path.parts[-2]
        parsed = self.curated_parser.parse_file(file_path)

        frontmatter = parsed["metadata"]
        raw_content = parsed["body"]

        sections = self.split_markdown_sections(raw_content)

        chunks: List[KnowledgeChunk] = []
        chunk_counter = 1

        for section_title, section_content in sections:
            text_parts = self.split_large_text(section_content, max_chars=900)

            for part in text_parts:
                chunk_id = f"{file_path.stem}_{chunk_counter}"

                tags = self.build_tags(
                    brain=brain,
                    file_stem=file_path.stem,
                    content=part,
                    extra_tags=frontmatter.get("tags", []),
                )

                chunk = KnowledgeChunk(
                    id=chunk_id,
                    brain=brain,
                    type=frontmatter.get("type", "secao_markdown"),
                    title=frontmatter.get("title", section_title),
                    content=part,
                    tags=tags,
                    priority=frontmatter.get("priority", 5),
                    source=str(file_path),
                    related_entities=frontmatter.get("related_entities", []),
                    metadata={
                        "file_name": file_path.name,
                        "section_title": section_title,
                        "chunk_index": chunk_counter,
                        "char_count": len(part),
                        "layer": frontmatter.get("layer"),
                        "style": frontmatter.get("style"),
                        "uses_db_alias": frontmatter.get("uses_db_alias", False),
                        "uses_slug": frontmatter.get("uses_slug", False),
                        "uses_serializer": frontmatter.get("uses_serializer", False),
                        "uses_form": frontmatter.get("uses_form", False),
                        "reason": frontmatter.get("reason", ""),
                    },
                )

                chunks.append(chunk)
                chunk_counter += 1

        total_chunks = len(chunks)

        for chunk in chunks:
            chunk.metadata["total_chunks_in_file"] = total_chunks

        return chunks