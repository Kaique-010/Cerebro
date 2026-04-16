import json
from openai import OpenAI

from app.core.config import settings
from app.schemas.executor import (
    ExecutorResult,
    ExecutorChunkRef,
    AnswerBlock,
    GeneratedCodeArtifacts,
)


class ExecutorService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EXECUTOR_MODEL

    def build_prompt(self, query: str, context_result: dict, mode: str = "answer") -> str:
        selected_chunks = context_result.get("selected_chunks", [])
        intent = context_result.get("intent", "geral")

        chunks_text = []

        for idx, chunk in enumerate(selected_chunks, start=1):
            chunks_text.append(
                f"""
[CHUNK {idx}]
ID: {chunk['id']}
BRAIN: {chunk['brain']}
TÍTULO: {chunk['title']}
SCORE_FINAL: {chunk['final_score']}
CONTEÚDO:
{chunk['content']}
""".strip()
            )

        joined_chunks = "\n\n".join(chunks_text)

        if mode == "codegen":
            return f"""
Você é um executor técnico de conhecimento com foco em geração de código Django no padrão horizontal.

Use SOMENTE os chunks fornecidos. Não invente regras fora do contexto.
Se faltar contexto, informe em "limitations".

Objetivo:
- Gerar código no padrão:
  - service (camada core)
  - serializer (DRF)
  - view REST
  - view web
- Incluir suporte multi-tenant via slug + banco com:
  from core.utils import get_db_from_slug

CONSULTA:
{query}

INTENÇÃO:
{intent}

CHUNKS SELECIONADOS:
{joined_chunks}

REGRAS:
- responder em português
- devolver apenas JSON válido
- manter arquitetura horizontal
- evitar conhecimento externo
- se uma camada não tiver contexto suficiente, devolver string vazia naquela camada e registrar limitação

FORMATO:
{{
  "answer_blocks": [
    {{
      "text": "resumo curto do que foi gerado",
      "supports": ["chunk_id_1"]
    }}
  ],
  "generated_code": {{
    "service": "código python",
    "serializer": "código python",
    "rest_view": "código python",
    "web_view": "código python"
  }},
  "limitations": [
    "limitação 1"
  ],
  "grounded": true
}}
""".strip()

        return f"""
Você é um executor técnico de conhecimento.

Responda a consulta usando SOMENTE os chunks fornecidos.
Não invente informações fora do contexto.
Se faltar contexto, diga isso nas limitações.
Responda em português.
Considere a intenção detectada.

Monte a resposta em blocos curtos.
Cada bloco deve citar quais IDs de chunks sustentam aquela afirmação.

CONSULTA:
{query}

INTENÇÃO:
{intent}

CHUNKS SELECIONADOS:
{joined_chunks}

REGRAS:
- cada bloco deve ser suportado por 1 ou mais chunk IDs
- não cite chunk que não sustenta diretamente a afirmação
- não use nenhum conhecimento externo
- devolva apenas JSON válido

FORMATO:
{{
  "answer_blocks": [
    {{
      "text": "texto do bloco",
      "supports": ["chunk_id_1", "chunk_id_2"]
    }}
  ],
  "limitations": [
    "limitação 1"
  ],
  "grounded": true
}}
""".strip()

    def safe_parse_json(self, raw_text: str) -> dict:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return {
                "answer_blocks": [
                    {
                        "text": raw_text.strip(),
                        "supports": []
                    }
                ],
                "limitations": ["A resposta não veio em JSON estrito"],
                "grounded": False,
            }

    def build_final_answer(self, answer_blocks: list[dict]) -> str:
        return "\n\n".join(
            block.get("text", "").strip()
            for block in answer_blocks
            if block.get("text", "").strip()
        ).strip()

    def execute(self, query: str, context_result: dict, mode: str = "answer") -> ExecutorResult:
        prompt = self.build_prompt(query=query, context_result=context_result, mode=mode)

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        raw_text = response.output_text
        data = self.safe_parse_json(raw_text)

        used_chunks = [
            ExecutorChunkRef(
                id=chunk["id"],
                brain=chunk["brain"],
                title=chunk["title"],
                final_score=chunk["final_score"],
            )
            for chunk in context_result.get("selected_chunks", [])
        ]

        answer_blocks = [
            AnswerBlock(
                text=block.get("text", ""),
                supports=block.get("supports", []),
            )
            for block in data.get("answer_blocks", [])
        ]

        final_answer = self.build_final_answer(data.get("answer_blocks", []))
        generated_code = GeneratedCodeArtifacts(
            service=data.get("generated_code", {}).get("service", ""),
            serializer=data.get("generated_code", {}).get("serializer", ""),
            rest_view=data.get("generated_code", {}).get("rest_view", ""),
            web_view=data.get("generated_code", {}).get("web_view", ""),
        )

        return ExecutorResult(
            query=query,
            answer_blocks=answer_blocks,
            final_answer=final_answer,
            limitations=data.get("limitations", []),
            grounded=bool(data.get("grounded", True)),
            used_chunks=used_chunks,
            generated_code=generated_code,
        )
