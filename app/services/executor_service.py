import json
from openai import OpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.executor import (
    ExecutorResult,
    ExecutorChunkRef,
    AnswerBlock,
    GeneratedCodeArtifacts,
)


class ExecutorService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        self.model = settings.OPENAI_EXECUTOR_MODEL
        self.logger = get_logger("service.executor")

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
- Gerar feature completa orientada ao pedido do usuário com os artefatos:
  - model (se necessário)
  - service (camada core)
  - serializer (DRF)
  - viewset (DRF)
  - urls (DRF)
  - testes
- Incluir suporte multi-tenant via slug + banco com:
  from core.utils import get_db_from_slug

REGRAS DE GERAÇÃO:
- services devem sempre usar Sum e nunca Max para agregações numéricas
- nunca repetir resolução de banco fora do service
- sempre validar parâmetros vindos de request
- evitar lógica de negócio na view/viewset
- seguir padrão multi-tenant com slug obrigatório

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
- preferir service para regra de negócio e viewset apenas como orquestração HTTP

FORMATO:
{{
  "answer_blocks": [
    {{
      "text": "resumo curto do que foi gerado",
      "supports": ["chunk_id_1"]
    }}
  ],
  "generated_code": {{
    "model": "código python",
    "service": "código python",
    "serializer": "código python",
    "viewset": "código python",
    "urls": "código python",
    "tests": "código python",
    "rest_view": "opcional para legado",
    "web_view": "opcional para legado"
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
- não crie blocos conclusivos genéricos
- cada bloco deve trazer orientação concreta, regra concreta ou limitação concreta
- evite frases vagas como "o padrão é aderente", "é reutilizável", "é testável", salvo se isso responder diretamente à consulta
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
        self.logger.info(
            "Execução iniciada | model=%s | mode=%s | selected_chunks=%s",
            self.model,
            mode,
            len(context_result.get("selected_chunks", [])),
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )
        self.logger.info("Execução concluída")

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
            model=data.get("generated_code", {}).get("model", ""),
            service=data.get("generated_code", {}).get("service", ""),
            serializer=data.get("generated_code", {}).get("serializer", ""),
            viewset=data.get("generated_code", {}).get("viewset", ""),
            urls=data.get("generated_code", {}).get("urls", ""),
            tests=data.get("generated_code", {}).get("tests", ""),
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
