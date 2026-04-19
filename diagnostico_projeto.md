# Diagnóstico Técnico do Cérebro (varredura do projeto)

## O que o projeto já faz bem

1. **Pipeline RAG bem separado por camadas**
   - `RetrievalBrain` orquestra classificação de intenção, embedding, busca semântica, rerank e montagem de contexto de forma limpa e legível.
   - Isso facilita evoluir cada etapa sem acoplamento excessivo.

2. **Modelo de contexto com score combinado e descarte explícito**
   - O `ContextBuilderService` calcula score final, registra motivos de descarte e gera um `context_text` rastreável.
   - É um bom fundamento para grounding e auditoria de resposta.

3. **Persistência incremental simples e útil**
   - `IncrementalMemoryService` salva decisões/interações em JSON, criando uma trilha de evolução do agente sem dependência de infra extra.

4. **Modo codegen já estruturado por artefatos**
   - O executor já retorna campos separados (`model`, `service`, `serializer`, `viewset`, `urls`, `tests`), o que permite validar geração por camada em vez de texto livre.

5. **Interface de chat funcional para operação rápida**
   - O app Streamlit já tem fluxo de conversa, modo de resposta e execução de tools em sidebar, útil para debug e validação manual.

---

## Principais pontos de melhoria (priorizados)

### P0 — Corrigir inconsistência ORM x schema SQL

**Problema:**
- O modelo SQLAlchemy (`KnowledgeChunkModel`) não está alinhado com o schema real (`init.sql`): o SQL inclui `tags`, `related_entities`, `metadata`, enquanto o model não define esses campos.
- O model usa `Vector(1536)` sem import explícito de `Vector`, o que pode quebrar ao importar o módulo.

**Risco:**
- Erro em runtime, manutenção difícil e divergência entre ingestão/consulta e modelagem.

**Próxima ação recomendada:**
- Unificar model + SQL (ou migrar completamente para SQLAlchemy modelado), incluindo todos os campos do banco e tipo vetorial de forma explícita.

---

### P0 — Multi-tenant/multi-db ainda não aplicado no runtime

**Problema:**
- A instrução de arquitetura pede slug obrigatório e roteamento por banco (`get_db_from_slug`), mas hoje a sessão DB é única (`SessionLocal`) e não recebe slug no fluxo de retrieval/ingest/chat.

**Risco:**
- Violação de isolamento por tenant e incompatibilidade com padrão arquitetural exigido.

**Próxima ação recomendada:**
- Introduzir `slug` como parâmetro obrigatório no fluxo (chat -> brain -> repository) e criar factory de sessão por tenant.

---

### P1 — Falta de validação/contrato para input das tools e chat

**Problema:**
- `ChatService.run_tool` aceita strings livres sem validação formal.
- Não há schema para payload de tool e limites para tamanho de query/decisão.

**Risco:**
- Erros silenciosos, payload inválido e baixa previsibilidade.

**Próxima ação recomendada:**
- Criar schemas Pydantic para entrada das tools e chamadas do chat, com mensagens de erro consistentes.

---

### P1 — Robustez do parser de resposta LLM

**Problema:**
- `safe_parse_json` depende de JSON perfeito; fallback vira texto bruto com `grounded=False`, sem tentativa de extração mais robusta.

**Risco:**
- Perda de estrutura gerada (especialmente em codegen) em respostas quase válidas.

**Próxima ação recomendada:**
- Implementar parser tolerante (ex.: extração do maior bloco JSON válido) antes do fallback final.

---

### P1 — Testes automatizados insuficientes

**Problema:**
- Não há suíte de testes cobrindo ingestão, retrieval, executor e tools.

**Risco:**
- Regressões frequentes e evolução insegura do codegen.

**Próxima ação recomendada:**
- Adicionar testes unitários para `ContextBuilderService`, `IntentService`, `ChatService` e parser do executor.
- Adicionar testes de contrato para saída `generated_code`.

---

### P2 — Falta de camada REST/web horizontal no backend

**Problema:**
- O projeto tem UI Streamlit e pipeline interno, mas ainda não expõe estrutura horizontal no padrão solicitado (`rest/serializers/views`, `web/forms/views/urls`) para consumo Django/DRF.

**Risco:**
- Distanciamento do padrão organizacional do time.

**Próxima ação recomendada:**
- Evoluir para módulos no padrão horizontal por feature (ex.: `chat/`, `knowledge/`) com service central, endpoints REST e views web.

---

## Backlog recomendado (ordem prática)

1. **P0.1** Alinhar model SQLAlchemy com `init.sql` + corrigir tipo `Vector`.
2. **P0.2** Tornar `slug` obrigatório em todos os fluxos e rotear sessão por tenant.
3. **P1.1** Criar schemas de entrada para chat/tools com validação.
4. **P1.2** Fortalecer parser de JSON do executor.
5. **P1.3** Criar suíte de testes (unit + contrato de codegen).
6. **P2.1** Refatorar para arquitetura horizontal Django/DRF por feature.

---

## Conclusão

O projeto já está em um ponto **muito bom de base**: pipeline RAG organizado, contexto explicável, memória incremental e geração estruturada por artefato.

Para subir de nível para produção consistente no seu padrão (multi-db, multi-slug e arquitetura horizontal), o foco deve ser:
- **isolamento multi-tenant real no runtime**,
- **consistência de modelo/banco**,
- **validação forte de entrada/saída**,
- **testes automatizados cobrindo o fluxo de geração**.
