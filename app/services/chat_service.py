from dataclasses import dataclass

from app.brain.executor_brain import ExecutorBrain
from app.brain.retrieval_brain import RetrievalBrain
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

    def available_tools(self) -> list[str]:
        return [
            "memory:list",
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

    def chat(self, query: str, top_k_vector: int = 8, top_k_final: int = 3) -> dict:
        retrieval = self.retrieval_brain.search(
            query=query,
            top_k_vector=top_k_vector,
            top_k_final=top_k_final,
        )

        context_result = retrieval["context_result"]
        execution = self.executor_brain.run(query=query, context_result=context_result)

        final_answer = execution["final_answer"]
        if self._should_include_code_example(query):
            final_answer = f"{final_answer}\n\nExemplo prático:\n{self._build_code_example()}"

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
        }
