class IntentService:
    """
    Classificador simples por heurística.
    Depois podemos trocar por LLM ou classificador dedicado.
    """

    IMPLEMENTACAO_KEYWORDS = [
        "crie", "criar", "implemente", "implementar", "monte", "montar",
        "faça", "fazer", "como estruturar", "como montar", "service",
        "view", "serializer", "endpoint", "django", "react native",
        "cbv", "api", "model", "código", "codigo"
    ]

    DOMINIO_KEYWORDS = [
        "regra", "domínio", "dominio", "fiscal", "empresa", "filial",
        "slug", "multi-tenant", "tenant", "banco", "db_alias",
        "negócio", "negocio"
    ]

    DEBUG_KEYWORDS = [
        "erro", "bug", "quebra", "falha", "problema", "não funciona",
        "nao funciona", "corrigir", "ajustar"
    ]

    EXPLICACAO_KEYWORDS = [
        "o que é", "oque é", "explique", "explica", "conceito",
        "como funciona", "qual a diferença", "por que"
    ]

    def classify(self, query: str) -> str:
        q = query.lower()

        if any(term in q for term in self.DEBUG_KEYWORDS):
            return "debug"

        if any(term in q for term in self.IMPLEMENTACAO_KEYWORDS):
            return "implementacao_tecnica"

        if any(term in q for term in self.DOMINIO_KEYWORDS):
            return "regra_dominio"

        if any(term in q for term in self.EXPLICACAO_KEYWORDS):
            return "explicacao"

        return "geral"