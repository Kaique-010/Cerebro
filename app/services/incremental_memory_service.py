import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IncrementalMemoryService:
    """Persistência incremental para decisões e histórico de chat."""

    def __init__(self, memory_file: str = "data/incremental_memory.json"):
        self.memory_path = Path(memory_file)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

    def _default_payload(self) -> dict[str, Any]:
        return {
            "decisions": [],
            "interactions": [],
            "updated_at": self._now_iso(),
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def load(self) -> dict[str, Any]:
        if not self.memory_path.exists():
            payload = self._default_payload()
            self.save(payload)
            return payload

        with self.memory_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = self._now_iso()
        with self.memory_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def add_decision(self, decision: str, source: str = "chat") -> dict[str, Any]:
        payload = self.load()
        payload["decisions"].append(
            {
                "decision": decision.strip(),
                "source": source,
                "created_at": self._now_iso(),
            }
        )
        self.save(payload)
        return payload

    def add_interaction(self, query: str, answer: str, grounded: bool) -> dict[str, Any]:
        payload = self.load()
        payload["interactions"].append(
            {
                "query": query.strip(),
                "answer": answer.strip(),
                "grounded": grounded,
                "created_at": self._now_iso(),
            }
        )
        self.save(payload)
        return payload
