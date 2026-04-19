# Verificação da Arquitetura Atual (estado real x alvo)

## Escopo da checagem
Checklist solicitado:

1. Coletor de conhecimento
2. Processador semântico
3. Base de memória
4. Harness de execução
5. Saída

---

## [1] Coletor de conhecimento

### Status geral: **PARCIALMENTE ATENDIDO**

### O que já acontece
- Leitura de `.md` em árvore de conhecimento via `MemoryBrain`.
- Conversão de arquivos em chunks via `ChunkerService`.
- Pipeline de ingestão com embedding + upsert no banco.

### Evidências técnicas
- `app/brain/memory_brain.py` (carrega markdown e exporta chunks).
- `app/services/chunker.py` (quebra por seção e tamanho).
- `app/services/ingest_service.py` (orquestra ingestão e persistência).

### O que falta
- Coletor dedicado para **models/services/utils/docs/exemplos bons** como fontes distintas com metadados padronizados.
- Regras de qualidade para separar “exemplo bom” de exemplo genérico.
- Política de versionamento por fonte e marcação de confiabilidade.

---

## [2] Processador semântico

### Status geral: **ATENDIDO (com gaps de robustez)**

### O que já acontece
- Chunking semântico por seção e parágrafo.
- Geração de embeddings com OpenAI.
- Classificação de intenção + rerank + score final.
- Metadados básicos (`file_name`, `section_title`, etc.).

### Evidências técnicas
- `app/services/chunker.py` (chunk por heading/parágrafo).
- `app/services/embedding_service.py` (embeddings).
- `app/services/intent_service.py` + `app/services/reranker_service.py`.
- `app/services/context_builder.py` (score combinado e descarte).

### O que falta
- Estratégia formal de **tags semânticas enriquecidas** (não só `brain`/`stem`).
- Observabilidade de qualidade do rerank (métricas offline).
- Parser mais resiliente para respostas não estritamente JSON.

---

## [3] Base de memória

### Status geral: **ATENDIDO (com inconsistências importantes)**

### O que já acontece
- Persistência vetorial em Postgres + `pgvector` (via `init.sql` e busca por `<=>`).
- Persistência incremental em JSON (`decisions` e `interactions`).

### Evidências técnicas
- `init.sql` (extensão vector e tabela `knowledge_chunks`).
- `app/repositories/knowledge_repository.py` (upsert + semantic_search).
- `app/services/incremental_memory_service.py` (JSON indexado simples).

### O que falta
- Alinhar ORM com schema real (campos e tipo vector no model SQLAlchemy).
- Definir claramente estratégia única de indexação híbrida (vetor + filtros + recência).
- Multi-tenant real no acesso à memória (slug obrigatório e roteamento por banco).

---

## [4] Harness de execução

### Status geral: **ATENDIDO (faltam dois pontos críticos)**

### O que já acontece
- Recebe tarefa/pergunta no `ChatService.chat`.
- Classifica intenção.
- Busca memórias semânticas.
- Monta contexto e chama agente executor.
- Possui “tools” básicas para memória/decisão.

### Evidências técnicas
- `app/services/chat_service.py` (orquestração principal).
- `app/brain/retrieval_brain.py` (intenção + busca + rerank + contexto).
- `app/services/executor_service.py` (prompt e chamada ao modelo).

### O que falta
- Catálogo de tools de domínio (hoje tools são mínimas).
- Aplicar padrão multi-db/multi-slug no fluxo de ponta a ponta (`get_db_from_slug`).

---

## [5] Saída

### Status geral: **ATENDIDO PARCIALMENTE**

### O que já acontece
- Saída textual em blocos com grounding por chunk.
- Saída de código estruturada (`model`, `service`, `serializer`, `viewset`, `urls`, `tests`).

### Evidências técnicas
- `app/schemas/executor.py` (estrutura da saída).
- `app/services/executor_service.py` (modo `answer` e `codegen`).
- `app/services/chat_service.py` (formatação da resposta final).

### O que falta
- Campo formal para **plano** e **ação executável** no schema de saída.
- Contrato de resposta por tipo (`response`, `code`, `plan`, `action`) com validação automática.
- Endpoint REST para consumo programático da saída (hoje foco em Streamlit/CLI).

---

## Conclusão objetiva

Você já tem o núcleo funcional dos 5 blocos, mas com nível de maturidade desigual:

- **Bem implementado:** [2] Processador semântico, [4] Harness base.
- **Funciona, mas precisa endurecer:** [1] Coletor e [3] Base de memória.
- **Incompleto para seu alvo final:** [5] Saída ainda sem contrato de `plano` e `ação`.

## Próximas entregas recomendadas (sequência direta)

1. Introduzir `slug` obrigatório e resolver DB com `get_db_from_slug` em todo o pipeline.
2. Alinhar model SQLAlchemy com `init.sql` e fechar lacunas de schema.
3. Evoluir schema de saída para `response + code + plan + action`.
4. Criar REST layer horizontal (serializers/views/urls) para execução externa.
5. Adicionar testes de contrato cobrindo o fluxo completo dos 5 blocos.
