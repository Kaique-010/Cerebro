from app.services.executor_service import ExecutorService


class ExecutorBrain:
    def __init__(self):
        self.executor_service = ExecutorService()

    def run(self, query: str, context_result: dict, mode: str = "answer") -> dict:
        result = self.executor_service.execute(
            query=query,
            context_result=context_result,
            mode=mode,
        )
        return result.model_dump()
