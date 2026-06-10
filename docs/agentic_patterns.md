# Agentic Patterns no refactor-os

Mapeamento das decisões de design baseadas nos 20 padrões de sistemas agentic
(referência: Antonio Gullí, *AI Agent Design Patterns*).

---

## Patterns Implementados (baseline)

Estes padrões já estão presentes na arquitetura desde a concepção do projeto.

| # | Pattern | Onde no código |
|---|---------|----------------|
| 1 | **Prompt Chaining (Pipeline)** | `RefactorService`: sequência determinística Detector → Recommender → Critic em `refactor_service.py` |
| 4 | **Reflection** | Loop Generator-Critic com `MAX_REFLECTION_ITERATIONS` em `RefactorService.run()` |
| 5 | **Tool Use (Function Calling)** | `ast_analyzer_tool`, `design_pattern_reference_tool`, `diff_generator_tool`, `syntax_checker_tool` em `app/tools/` |
| 7 | **Multi-Agent Collaboration** | Três agentes especializados (`DetectorAgent`, `RecommenderAgent`, `CriticAgent`) com papéis exclusivos |
| 14 | **Knowledge Retrieval (RAG)** | PgVector + 5 arquivos `.md` de patterns via `KnowledgeTools` em `app/knowledge/` |
| 19 | **Evaluation and Monitoring** | Endpoints `/evaluate/{detector,refactor,critic,all}` — métricas independentes por agente contra `dataset/ground_truth.json` e `dataset/critic_truth.json` (ou amostras enviadas ad-hoc) |

---

## Patterns Adicionados (hardening — branch `claude/agentic-patterns-hardening`)

### 18 · Guardrails

**Problema resolvido:** `source_code` chegava sem validação — um arquivo de 500k linhas ou
vazio causaria comportamento indefinido nos agentes. Pior: `CriticAgent` incluía `ShellTools()`
(execução arbitrária de shell), que é um vetor de execução de código externo não intencional.

**Implementação:**
- `source_code` em `RefactorRequest` ganhou `min_length=1` e `max_length=50_000` via Pydantic.
  O FastAPI retorna HTTP 422 automaticamente se a validação falhar — sem alterar a lógica dos agentes.
- `ShellTools()` foi removido de `CriticAgent`. As ferramentas `syntax_checker_tool` e
  `diff_generator_tool` já cobrem 100% do que o Critic precisa; o ShellTools era redundante e perigoso.

**Arquivos:** `app/core/schemas.py`, `app/agents/critic_agent.py`

---

### 11 · Goal Setting and Monitoring (critérios SMART no Critic)

**Problema resolvido:** O Critic avaliava com instruções vagas ("avalie se o pattern foi aplicado
corretamente"). Com LLMs probabilísticos, critérios vagos geram decisões inconsistentes entre
iterações, tornando o `accuracy` do `/evaluate/refactor` não-reproduzível.

**Implementação:** `CRITIC_INSTRUCTIONS` em `app/core/prompts.py` substituiu a seção de avaliação
por 5 critérios numerados e binários (SMART):

1. `syntax_checker_tool` retorna sem erros de sintaxe — verificável objetivamente.
2. Nenhuma branch lógica (if/else, case) do original foi removida — verificável via diff.
3. O `applied_pattern` bate exatamente com o mapeamento `SMELL_TO_PATTERN[smell_type]`.
4. Assinaturas públicas (classes e métodos públicos) foram preservadas ou refatoradas intencionalmente.
5. Nenhum import externo novo foi introduzido além dos necessários pelo pattern aplicado.

Todos os 5 devem ser `True` para `is_approved=true`. Caso contrário, a `critique` deve
referenciar o número do critério que falhou.

**Arquivos:** `app/core/prompts.py`

---

### 12 · Exception Handling and Recovery

**Problema resolvido:** Qualquer falha de rede, timeout na Groq, ou resposta malformada do LLM
(`output_schema` não respeitado) propagava uma exceção não tratada até o FastAPI, resultando em
HTTP 500 sem informação útil para o cliente ou para o pipeline de avaliação.

**Implementação:** Cada estágio do `RefactorService` (`detect`, `propose`, `review`) passou a
capturar exceções e retornar fallbacks estruturados:

- `detect()`: em caso de falha, retorna `SmellDetection(has_smell=False, smell_type=NO_SMELL, reasoning="[erro]")`.
- `propose()` e `review()`: em caso de falha, o `run()` encerra a iteração atual e retorna
  `RefactorResult(approved=False, iterations=N)` com `error` preenchido — sem propagar 500.
- Todos os erros são logados com `logger.exception(...)` para rastreabilidade.

O campo `error: str | None` foi adicionado a `RefactorResult` para surfaçar a mensagem ao cliente.

**Arquivos:** `app/services/refactor_service.py`, `app/core/schemas.py`

---

## Patterns Descartados (e por quê)

| Pattern | Motivo do descarte |
|---------|-------------------|
| **2 · Routing** | Só há 5 smells e o Detector já classifica — um router seria duplicação. |
| **3 · Parallelization** | Fluxo é sequencial por dependência de dados (saída de cada estágio é input do próximo). |
| **6 · Planning** | Escopo fixo (5 patterns, 1 refactor por arquivo). Não há plano multi-etapa a formular. |
| **8 · Memory Management** | Pipeline stateless por arquivo. O PgVector já provê o "longo prazo" via RAG. |
| **9 · Learning and Adaptation** | Fora do escopo acadêmico (sem RL/fine-tuning). |
| **10 · MCP** | Overhead de infraestrutura sem ganho — todas as tools são internas ao projeto. |
| **13 · HITL** | Os endpoints `/evaluate/*` contra ground truth substituem supervisão humana para fins acadêmicos. |
| **16 · Resource-Aware Optimization** | Modelo único (Llama 3.3 70B). Roteamento Flash/Pro não se aplica. |
| **17 · Reasoning Techniques (CoT/ToT/ReAct)** | Llama 3.3 já aplica CoT implícito; ReAct é contraditório com pipeline determinístico. |
| **20 · Prioritization** | Uma tarefa por vez, sem fila concorrente de objetivos. |

> **Nota sobre Team (Agno):** O `agno.Team` foi avaliado e descartado — veja `docs/architecture.md`
> para a justificativa detalhada. Em resumo: o Team usa um LLM como orquestrador, o que quebra
> o determinismo do pipeline e impede medir cada estágio individualmente para os endpoints `/evaluate/*`.
