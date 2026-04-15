import json
from openai import OpenAI

from app.core.config import settings


class RerankerService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_RERANK_MODEL

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not candidates:
            return []

        compact_candidates = []
        for idx, item in enumerate(candidates, start=1):
            compact_candidates.append({
                "candidate_id": idx,
                "chunk_id": item["id"],
                "title": item["title"],
                "brain": item["brain"],
                "content": item["content"][:1200],
                "vector_score": item.get("score", 0),
            })

        prompt = f"""
Você é um reranker semântico.
Sua tarefa é reordenar os candidatos mais relevantes para responder à consulta.

Consulta:
{query}

Candidatos:
{json.dumps(compact_candidates, ensure_ascii=False, indent=2)}

Regras:
- priorize relevância semântica real
- priorize chunks que respondem diretamente
- considere o título, brain e conteúdo
- pode usar o vector_score apenas como sinal secundário
- devolva apenas JSON válido
- formato:
{{
  "ranking": [
    {{
      "candidate_id": 3,
      "score": 0.98,
      "reason": "..."
    }}
  ]
}}
"""

        # O endpoint "completions" espera "prompt". Para usar "messages", use chat.completions.
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise ValueError("Reranker retornou resposta vazia")
        data = json.loads(raw_text)

        ranking_map = {
            item["candidate_id"]: {
                "rerank_score": item["score"],
                "rerank_reason": item["reason"],
            }
            for item in data["ranking"]
        }

        ranked = []
        for idx, original in enumerate(candidates, start=1):
            if idx in ranking_map:
                merged = dict(original)
                merged.update(ranking_map[idx])
                ranked.append(merged)

        ranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        return ranked[:top_k]
