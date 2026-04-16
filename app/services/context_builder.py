from app.schemas.context import (
    ContextBuildResult,
    ScoredChunk,
    DiscardedChunk,
)


class ContextBuilderService:
    def __init__(self):
        self.generic_brains = {"identidade"}

        self.conceitual_brains = {
            "dominio",
            "padroes",
            "identidade",
        }

        self.exemplo_real_brains = {
            "services",
            "views_rest",
            "views_web",
            "serializers",
            "autocompletes",
        }

        self.infra_layers = {
            "utils",
            "mixins",
            "middleware",
        }

    def compute_query_boost(
        self,
        *,
        query: str,
        brain: str,
        metadata: dict
    ) -> float:
        q = query.lower()
        boost = 0.0

        dominio_terms = {
            "slug", "tenant", "banco", "db_alias",
            "empresa", "filial", "multi-tenant"
        }
        service_terms = {
            "service", "services", "regra", "negócio", "negocio"
        }
        rest_terms = {
            "api", "endpoint", "viewset", "serializer", "rest"
        }
        web_terms = {
            "form", "template", "createview", "listview", "updateview", "web"
        }

        layer = (metadata or {}).get("layer")
        style = (metadata or {}).get("style")

        if any(term in q for term in dominio_terms):
            if brain == "dominio":
                boost += 0.12
            if layer in self.infra_layers:
                boost += 0.12
            elif metadata.get("uses_db_alias") or metadata.get("uses_slug"):
                boost += 0.05

        if any(term in q for term in service_terms):
            if brain in {"padroes", "services"}:
                boost += 0.08
            if layer == "service":
                boost += 0.06

        if any(term in q for term in rest_terms):
            if layer == "view_rest" or style == "rest":
                boost += 0.08
            if brain in {"views_rest", "serializers"}:
                boost += 0.05

        if any(term in q for term in web_terms):
            if layer == "view_web" or style == "web":
                boost += 0.08
            if brain == "views_web":
                boost += 0.05

        return round(boost, 4)

    def compute_final_score(
        self,
        *,
        query: str,
        vector_score: float,
        rerank_score: float,
        priority: int,
        brain: str,
        intent: str,
        metadata: dict
    ) -> float:
        final_score = (vector_score * 0.35) + (rerank_score * 0.65)
        final_score += (priority / 100.0)

        query_boost = self.compute_query_boost(
            query=query,
            brain=brain,
            metadata=metadata or {},
        )
        final_score += query_boost

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
        brain = item["brain"]

        if intent in {"implementacao_tecnica", "debug"} and brain == "identidade":
            has_specific = any(
                selected.brain in {
                    "padroes", "dominio", "services", "views_rest",
                    "views_web", "serializers", "mixins", "utils",
                    "autocompletes", "exemplos_codigo", "erros_conhecidos"
                }
                for selected in best_selected
            )
            if has_specific:
                return "Chunk mais genérico que os já selecionados para consulta operacional"

        return None

    def _is_conceitual(self, chunk: ScoredChunk) -> bool:
        return chunk.brain in self.conceitual_brains

    def _is_exemplo_real(self, chunk: ScoredChunk) -> bool:
        return chunk.brain in self.exemplo_real_brains

    def _is_infra_tenant(self, chunk: ScoredChunk) -> bool:
        metadata = chunk.metadata or {}
        layer = metadata.get("layer")

        return (
            layer in self.infra_layers
            or chunk.brain in {"utils", "mixins"}
        )

    def _infra_rank(self, chunk: ScoredChunk) -> int:
        metadata = chunk.metadata or {}
        layer = metadata.get("layer")

        if layer == "utils" or chunk.brain == "utils":
            return 0
        if layer in {"mixins", "middleware"} or chunk.brain == "mixins":
            return 1
        return 2

    def _query_needs_tenant_infra(self, query: str) -> bool:
        q = query.lower()
        return any(
            term in q for term in [
                "slug", "tenant", "banco", "db_alias",
                "empresa", "filial", "multi-tenant"
            ]
        )

    def _pick_best_by_group(
        self,
        *,
        candidates: list[ScoredChunk],
        selected_ids: set[str],
        selected_brains: set[str],
        predicate,
    ) -> ScoredChunk | None:
        for chunk in candidates:
            if chunk.id in selected_ids:
                continue
            if chunk.brain in selected_brains:
                continue
            if predicate(chunk):
                return chunk
        return None

    def _pick_best_infra_tenant(
        self,
        *,
        candidates: list[ScoredChunk],
        selected_ids: set[str],
        selected_brains: set[str],
    ) -> ScoredChunk | None:
        strict_matches = [
            chunk for chunk in candidates
            if chunk.id not in selected_ids
            and chunk.brain not in selected_brains
            and self._is_infra_tenant(chunk)
        ]

        if strict_matches:
            strict_matches.sort(key=lambda c: (self._infra_rank(c), -c.final_score))
            return strict_matches[0]

        return None

    def select_by_roles(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        top_k_final: int
    ) -> tuple[list[ScoredChunk], dict[str, str]]:
        selected: list[ScoredChunk] = []
        selected_ids: set[str] = set()
        selected_brains: set[str] = set()
        reasons_by_id: dict[str, str] = {}

        # 1. Base conceitual
        chunk = self._pick_best_by_group(
            candidates=candidates,
            selected_ids=selected_ids,
            selected_brains=selected_brains,
            predicate=self._is_conceitual,
        )
        if chunk:
            selected.append(chunk)
            selected_ids.add(chunk.id)
            selected_brains.add(chunk.brain)
            reasons_by_id[chunk.id] = "Selecionado como base conceitual da resposta"

        # 2. Exemplo real do projeto
        chunk = self._pick_best_by_group(
            candidates=candidates,
            selected_ids=selected_ids,
            selected_brains=selected_brains,
            predicate=self._is_exemplo_real,
        )
        if chunk and len(selected) < top_k_final:
            selected.append(chunk)
            selected_ids.add(chunk.id)
            selected_brains.add(chunk.brain)
            reasons_by_id[chunk.id] = "Selecionado como exemplo real do projeto"

        # 3. Infra multi-tenant, se a query pedir
        if self._query_needs_tenant_infra(query):
            chunk = self._pick_best_infra_tenant(
                candidates=candidates,
                selected_ids=selected_ids,
                selected_brains=selected_brains,
            )
            if chunk and len(selected) < top_k_final:
                selected.append(chunk)
                selected_ids.add(chunk.id)
                selected_brains.add(chunk.brain)
                reasons_by_id[chunk.id] = "Selecionado como infraestrutura real de multi-tenant"

        # 4. Completa por score sem repetir brain, se possível
        for chunk in candidates:
            if len(selected) >= top_k_final:
                break
            if chunk.id in selected_ids:
                continue
            if chunk.brain in selected_brains:
                continue

            selected.append(chunk)
            selected_ids.add(chunk.id)
            selected_brains.add(chunk.brain)
            reasons_by_id[chunk.id] = "Selecionado para complementar o contexto por score combinado"

        # 5. Se ainda faltar vaga, completa mesmo repetindo brain
        for chunk in candidates:
            if len(selected) >= top_k_final:
                break
            if chunk.id in selected_ids:
                continue

            selected.append(chunk)
            selected_ids.add(chunk.id)
            selected_brains.add(chunk.brain)
            reasons_by_id[chunk.id] = "Selecionado para complementar o contexto por score combinado"

        selected.sort(key=lambda x: x.final_score, reverse=True)
        return selected[:top_k_final], reasons_by_id

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
        scored_candidates: list[ScoredChunk] = []
        discarded: list[DiscardedChunk] = []

        for item in reranked_items:
            vector_score = float(item.get("score", 0))
            rerank_score = float(item.get("rerank_score", 0))
            priority = int(item.get("priority", 5))
            metadata = item.get("metadata", {}) or {}

            final_score = self.compute_final_score(
                query=query,
                vector_score=vector_score,
                rerank_score=rerank_score,
                priority=priority,
                brain=item["brain"],
                intent=intent,
                metadata=metadata,
            )

            discard_reason = self.should_discard(
                item=item,
                intent=intent,
                best_selected=scored_candidates,
            )

            if discard_reason:
                discarded.append(
                    DiscardedChunk(
                        id=item["id"],
                        reason=discard_reason
                    )
                )
                continue

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
                metadata=metadata,
                selection_reason=item.get("rerank_reason", "Selecionado por relevância combinada"),
            )

            scored_candidates.append(scored_chunk)

        scored_candidates.sort(key=lambda x: x.final_score, reverse=True)

        selected, role_reasons = self.select_by_roles(
            query=query,
            candidates=scored_candidates,
            top_k_final=top_k_final,
        )

        for chunk in selected:
            if chunk.id in role_reasons:
                chunk.selection_reason = role_reasons[chunk.id]

        selected_ids = {item.id for item in selected}

        for chunk in scored_candidates:
            if chunk.id not in selected_ids and not any(d.id == chunk.id for d in discarded):
                discarded.append(
                    DiscardedChunk(
                        id=chunk.id,
                        reason="Não entrou no contexto final após seleção por papéis e score combinado"
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