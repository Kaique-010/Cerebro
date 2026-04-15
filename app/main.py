import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

from app.services.ingest_service import IngestService
from app.brain.retrieval_brain import RetrievalBrain
from app.brain.executor_brain import ExecutorBrain


def run_ingest():
    service = IngestService()
    total = service.run()
    print(f"Ingestão concluída. Total de chunks gravados: {total}")


def run_query():
    retrieval_brain = RetrievalBrain()
    executor_brain = ExecutorBrain()

    query = "como o agente deve estruturar services e respeitar multi-tenant com slug e banco?"

    retrieval_result = retrieval_brain.search(
        query=query,
        top_k_vector=8,
        top_k_final=2,
    )

    context_result = retrieval_result["context_result"]

    execution_result = executor_brain.run(
        query=query,
        context_result=context_result,
    )

    print("\n=== QUERY ===")
    print(query)

    print("\n=== INTENÇÃO ===")
    print(retrieval_result["intent"])

    print("\n=== CHUNKS SELECIONADOS ===")
    for item in context_result["selected_chunks"]:
        print(
            f"[SELECTED] {item['id']} | {item['brain']} | "
            f"final={item['final_score']:.4f}"
        )
        print(f"Título: {item['title']}")
        print(f"Motivo: {item['selection_reason']}")
        print("-" * 60)

    print("\n=== BLOCOS DA RESPOSTA ===")
    for idx, block in enumerate(execution_result["answer_blocks"], start=1):
        print(f"[BLOCO {idx}]")
        print(block["text"])
        print(f"Suporte: {', '.join(block['supports']) if block['supports'] else 'sem suporte'}")
        print("-" * 60)

    print("\n=== RESPOSTA FINAL ===")
    print(execution_result["final_answer"])

    print("\n=== LIMITAÇÕES ===")
    if execution_result["limitations"]:
        for limitation in execution_result["limitations"]:
            print(f"- {limitation}")
    else:
        print("Nenhuma limitação relevante informada.")

    print("\n=== CHUNKS USADOS ===")
    for item in execution_result["used_chunks"]:
        print(
            f"[USED] {item['id']} | {item['brain']} | "
            f"{item['title']} | score={item['final_score']:.4f}"
        )

    with open("data/executor_result.json", "w", encoding="utf-8") as f:
        json.dump(execution_result, f, ensure_ascii=False, indent=2)

    print("\nArquivo gerado em: data/executor_result.json")


if __name__ == "__main__":
    run_ingest()
    run_query()