from dataclasses import dataclass
from typing import Iterator

from app.brain.executor_brain import ExecutorBrain
from app.brain.retrieval_brain import RetrievalBrain
from app.core.logging import get_logger
from app.services.incremental_memory_service import IncrementalMemoryService


@dataclass
class ToolResult:
    name: str
    output: str


class ChatService:
    """Orquestra chat + memória incremental + executor de tools."""

    def __init__(self):
        self.retrieval_brain = RetrievalBrain()
        self.executor_brain = ExecutorBrain()
        self.memory = IncrementalMemoryService()
        self.logger = get_logger("chat.service")

    def available_tools(self) -> list[str]:
        return [
            "memory:list",
            "memory:stats",
            "decision:add",
            "decision:list",
        ]

    def run_tool(self, tool_name: str, value: str = "") -> ToolResult:
        payload = self.memory.load()

        if tool_name == "memory:list":
            output = (
                f"Decisões: {len(payload['decisions'])} | "
                f"Interações: {len(payload['interactions'])}"
            )
            return ToolResult(name=tool_name, output=output)

        if tool_name == "decision:add":
            if not value.strip():
                return ToolResult(name=tool_name, output="Informe uma decisão para salvar.")
            self.memory.add_decision(value, source="tool")
            return ToolResult(name=tool_name, output="Decisão salva com sucesso.")

        if tool_name == "decision:list":
            decisions = payload.get("decisions", [])
            if not decisions:
                return ToolResult(name=tool_name, output="Nenhuma decisão registrada ainda.")

            lines = [f"{idx}. {item['decision']}" for idx, item in enumerate(decisions, start=1)]
            return ToolResult(name=tool_name, output="\n".join(lines))

        if tool_name == "memory:stats":
            stats = self.memory.get_stats()
            return ToolResult(
                name=tool_name,
                output=(
                    f"file={stats['memory_file']} | decisions={stats['total_decisions']} | "
                    f"interactions={stats['total_interactions']} | updated_at={stats['updated_at']}"
                ),
            )

        return ToolResult(name=tool_name, output="Tool não reconhecida.")

    def _should_include_code_example(self, query: str) -> bool:
        flags = [
            "código",
            "codigo",
            "exemplo",
            "snippet",
            "implementação",
            "implementation",
        ]
        q = query.lower()
        return any(flag in q for flag in flags)

    def _build_code_example(self) -> str:
        return (
            "```python\n"
            "from app.services.chat_service import ChatService\n\n"
            "chat = ChatService()\n"
            "result = chat.chat('me dê um exemplo de serializer DRF')\n"
            "print(result['answer'])\n"
            "```"
        )

    def _format_generated_code(self, generated_code: dict) -> str:
        blocks: list[str] = []
        mapping = [
            ("model", "Model"),
            ("service", "Service"),
            ("serializer", "Serializer"),
            ("viewset", "ViewSet"),
            ("urls", "URLs"),
            ("tests", "Testes"),
            ("rest_view", "View REST (legado)"),
            ("web_view", "View Web (legado)"),
        ]
        for key, label in mapping:
            content = generated_code.get(key, "").strip()
            if content:
                blocks.append(f"### {label}\n```python\n{content}\n```")
        return "\n\n".join(blocks).strip()

    def stream_text(self, text: str, chunk_size: int = 80) -> Iterator[str]:
        normalized = text or ""
        for idx in range(0, len(normalized), chunk_size):
            yield normalized[idx: idx + chunk_size]

    def _extract_decision_payload(self, query: str) -> str:
        markers = ["decisão:", "decisao:", "salvar decisão:", "salvar decisao:"]
        q_lower = query.lower()
        for marker in markers:
            if marker in q_lower:
                start = q_lower.find(marker) + len(marker)
                return query[start:].strip()
        return ""

    def _auto_tool_plan(self, query: str, intent: str) -> list[tuple[str, str]]:
        q_lower = query.lower()
        plan: list[tuple[str, str]] = []

        if "salvar decisão" in q_lower or "salvar decisao" in q_lower or "registrar decisão" in q_lower:
            payload = self._extract_decision_payload(query)
            if payload:
                plan.append(("decision:add", payload))

        if "listar decisões" in q_lower or "listar decisoes" in q_lower:
            plan.append(("decision:list", ""))

        if "memória" in q_lower or "memoria" in q_lower or intent == "debug":
            plan.append(("memory:stats", ""))

        return plan

    def chat(
        self,
        query: str,
        top_k_vector: int = 8,
        top_k_final: int = 3,
        mode: str = "answer",
    ) -> dict:
        retrieval = self.retrieval_brain.search(
            query=query,
            top_k_vector=top_k_vector,
            top_k_final=top_k_final,
        )
        self.logger.info(
            "Orquestração chat | intent=%s | selected_chunks=%s",
            retrieval["intent"],
            len(retrieval["context_result"]["selected_chunks"]),
        )

        context_result = retrieval["context_result"]
        execution = self.executor_brain.run(
            query=query,
            context_result=context_result,
            mode=mode,
        )

        auto_tools_executed: list[dict] = []
        for tool_name, tool_payload in self._auto_tool_plan(query=query, intent=retrieval["intent"]):
            tool_result = self.run_tool(tool_name, tool_payload)
            self.logger.info(
                "Tool automática executada | tool=%s | payload=%s",
                tool_name,
                tool_payload[:120],
            )
            auto_tools_executed.append(
                {
                    "tool": tool_result.name,
                    "payload": tool_payload,
                    "output": tool_result.output,
                }
            )

        final_answer = execution["final_answer"]
        if mode == "codegen":
            generated_code = self._format_generated_code(execution.get("generated_code", {}))
            if generated_code:
                final_answer = f"{final_answer}\n\n{generated_code}".strip()
        elif self._should_include_code_example(query):
            final_answer = f"{final_answer}\n\nExemplo prático:\n{self._build_code_example()}"

        if auto_tools_executed:
            tool_lines = [
                f"- {item['tool']}: {item['output']}"
                for item in auto_tools_executed
            ]
            final_answer = (
                f"{final_answer}\n\n### Tools automáticas por intenção\n"
                + "\n".join(tool_lines)
            ).strip()

        self.memory.add_interaction(
            query=query,
            answer=final_answer,
            grounded=execution["grounded"],
        )

        return {
            "query": query,
            "intent": retrieval["intent"],
            "answer": final_answer,
            "limitations": execution["limitations"],
            "grounded": execution["grounded"],
            "used_chunks": execution["used_chunks"],
            "generated_code": execution.get("generated_code", {}),
            "auto_tools_executed": auto_tools_executed,
        }
