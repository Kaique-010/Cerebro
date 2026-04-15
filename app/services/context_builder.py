from app.schemas.context import (
    ContextBuildResult,
    ScoredChunk,
    DiscardedChunk,
)


class ContextBuilderService:
    def __init__(self):
        self.generic_brains = {"identidade"}

    def compute_final_score(
        self,
        *,
        vector_score: float,
        rerank_score: float,
        priority: int,
        brain: str,
        intent: str
    ) -> float:
        """
        Fórmula inicial:
        - rerank manda mais
        - vector ajuda a ancorar
        - priority dá bônus
        - identidade sofre leve penalidade em consulta operacional
        """
        final_score = (vector_score * 0.35) + (rerank_score * 0.65)
        final_score += (priority / 100.0)

        if intent in {"implementacao_tecnica", "debug"} and brain in self.generic_brains:
            final_score -= 0.08

        return round(final_score, 4)

    def should_discard(
        self,
        *,
        item: dict,
        intent: str,
        best_selected: list[ScoredChunk]
    ) -> str | None:
        """
        Retorna motivo do descarte ou None.
        """
        brain = item["brain"]

        if intent in {"implementacao_tecnica", "debug"} and brain == "identidade":
            has_specific = any(
                selected.brain in {"padroes", "dominio", "exemplos_codigo", "erros_conhecidos"}
                for selected in best_selected
            )
            if has_specific:
                return "Chunk mais genérico que os já selecionados para consulta operacional"

        return None

    def build_context_text(self, query: str, intent: str, selected_chunks: list[ScoredChunk]) -> str:
        parts = [
            f"CONSULTA DO USUÁRIO:\n{query}",
            f"\nINTENÇÃO DETECTADA:\n{intent}",
            "\nCONTEXTO SELECIONADO:"
        ]

        for idx, chunk in enumerate(selected_chunks, start=1):
            parts.append(
                f"""
[{idx}] ID: {chunk.id}
BRAIN: {chunk.brain}
TÍTULO: {chunk.title}
SCORE FINAL: {chunk.final_score}
MOTIVO DA SELEÇÃO: {chunk.selection_reason}
CONTEÚDO:
{chunk.content}
""".strip()
            )

        return "\n\n".join(parts).strip()

    def select(
        self,
        *,
        query: str,
        intent: str,
        reranked_items: list[dict],
        top_k_final: int = 3
    ) -> ContextBuildResult:
        selected: list[ScoredChunk] = []
        discarded: list[DiscardedChunk] = []

        for item in reranked_items:
            vector_score = float(item.get("score", 0))
            rerank_score = float(item.get("rerank_score", 0))
            priority = int(item.get("priority", 5))

            final_score = self.compute_final_score(
                vector_score=vector_score,
                rerank_score=rerank_score,
                priority=priority,
                brain=item["brain"],
                intent=intent,
            )

            discard_reason = self.should_discard(
                item=item,
                intent=intent,
                best_selected=selected,
            )

            if discard_reason:
                discarded.append(
                    DiscardedChunk(
                        id=item["id"],
                        reason=discard_reason
                    )
                )
                continue

            selection_reason = item.get("rerank_reason", "Selecionado por relevância combinada")

            scored_chunk = ScoredChunk(
                id=item["id"],
                brain=item["brain"],
                title=item["title"],
                content=item["content"],
                vector_score=vector_score,
                rerank_score=rerank_score,
                final_score=final_score,
                priority=priority,
                tags=item.get("tags", []),
                source=item.get("source", ""),
                metadata=item.get("metadata", {}),
                selection_reason=selection_reason,
            )

            selected.append(scored_chunk)

        selected.sort(key=lambda x: x.final_score, reverse=True)
        selected = selected[:top_k_final]

        selected_ids = {item.id for item in selected}

        # tudo que não entrou vira descarte com motivo simples
        for item in reranked_items:
            if item["id"] not in selected_ids and not any(d.id == item["id"] for d in discarded):
                discarded.append(
                    DiscardedChunk(
                        id=item["id"],
                        reason="Não entrou no top final após score combinado"
                    )
                )

        context_text = self.build_context_text(
            query=query,
            intent=intent,
            selected_chunks=selected
        )

        return ContextBuildResult(
            query=query,
            intent=intent,
            selected_chunks=selected,
            discarded_chunks=discarded,
            context_text=context_text,
        )