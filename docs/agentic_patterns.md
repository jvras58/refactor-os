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
| 5 | **Tool Use (Function Calling)** | `ast_analyzer_tool`, `diff_generator_tool`, `syntax_checker_tool` em `app/tools/` |
| 7 | **Multi-Agent Collaboration** | Três agentes especializados (`DetectorAgent`, `RecommenderAgent`, `CriticAgent`) com papéis exclusivos |
| 14 | **Skills (substitui RAG)** | `agno.skills.Skills(loaders=[LocalSkills("app/skills")])` injetado no Recommender — uma `SKILL.md` por pattern, carregada sob demanda via `get_skill_instructions`. Substituiu o RAG via PgVector + HuggingFace embeddings. Ver §15 abaixo. |
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

### 15 · Few-Shot Prompting via Skills (Recommender) + inline (Critic)

**Problema resolvido:** os prompts originais do Recommender e do Critic eram
**zero-shot** — descreviam o que fazer, mas não mostravam exemplos canônicos da
saída esperada. Resultado prático no baseline (`dataset/reports/evaluation_baseline.md`):

| Agente | Métrica chave (baseline) | Gap |
|---|---|---|
| Detector | F1 = 1.000 | — (saturado) |
| Recommender | Accuracy = 0.600 | "API pública preservada" = 0.600 |
| Critic | F1 = 0.941 | 1 false reject |

O Recommender errava sobretudo o **critério 4** do Critic ("assinaturas públicas
preservadas") — sintaxe e pattern saíam corretos, mas a função pública mudava
de assinatura e o wrapper fino não era escrito. Esse é exatamente o tipo de
padrão que few-shot resolve: o LLM imita a forma do exemplo.

**Estratégia adotada (em duas camadas):**

#### Recommender → few-shot via Agno Skills (lazy-load)

Os exemplos canônicos vivem em [`app/skills/`](../app/skills/) como 5 `SKILL.md`
— uma por pattern. O agente recebe `Skills(loaders=[LocalSkills("app/skills")])`
e, no prompt por chamada, é instruído a chamar
`get_skill_instructions(name="<skill>")` antes de propor o código. O nome do
skill é resolvido deterministicamente em
[`refactor_service.py`](../app/services/refactor_service.py) via
`_PATTERN_TO_SKILL[expected_pattern]` e injetado direto no prompt — o LLM não
precisa adivinhar.

```
app/skills/
├── strategy-pattern/SKILL.md
├── builder-parameter-object/SKILL.md
├── facade-srp/SKILL.md
├── dependency-injection/SKILL.md
└── template-method/SKILL.md
```

Cada `SKILL.md` tem YAML frontmatter (`name`, `description`) + corpo com:
intent, estrutura canônica, regras estritas, exemplo problema→solução completo
(extraído de `dataset/examples/` + `dataset/solutions/correct/`), justificativa
arquitetural numerada e benefícios esperados. **Apenas a `description` curta
vai pro system prompt o tempo todo**; o corpo do SKILL só entra no contexto
quando o agente chama `get_skill_instructions`.

#### Critic → few-shot inline (cross-pattern)

Os 3 exemplos do Critic ficam diretos em
[`CRITIC_INSTRUCTIONS`](../app/core/prompts.py) porque cobrem padrões
transversais (aprovação amarrada aos 5 critérios + 2 rejeições mostrando o
formato "Critério N falhou: ... Ação: ..."). Particionar em skills não traz
ganho aqui — todo Critic precisa ver os 3.

#### Detector → mantido zero-shot

O baseline já marcava F1 = 1.000 sobre 20 amostras. Adicionar exemplos ali só
introduz ruído. Decisão validada empiricamente: a primeira tentativa de
few-shot no Detector causou regressão (modelo retornando string vazia em vez de
`SmellDetection`) e foi revertida.

**Por que skills em vez de manter os exemplos inline no prompt do Recommender?**
1. **Prompt base 60% menor.** Antes, os 2 exemplos inline custavam ~3k chars
   carregados em **toda** invocação do Recommender — mesmo iterações de
   reflection. Agora o LLM só puxa o skill que importa pro smell em questão.
2. **Modularidade.** Editar o exemplo de Strategy é 1 commit em
   `app/skills/strategy-pattern/SKILL.md`. Antes, era mexer em `prompts.py` e
   correr o risco de quebrar o JSON do exemplo de outro pattern por engano.
3. **Removeu PgVector + HuggingFace.** Skills cobrem o mesmo papel que o RAG
   antigo (injetar conhecimento canônico de patterns), mas sem embeddings.
   Detalhes do trade-off na seção §16 abaixo.

**Tradeoff assumido:**
- O Recommender agora faz **1 tool call a mais por iteração** (`get_skill_instructions`).
  Latência +1 round-trip ao Mistral, mas o prompt base ficou menor e o exemplo
  carregado é o relevante (não 2 fixos).
- Skills só entram em jogo se o LLM efetivamente chamar a tool — daí o prompt
  por chamada **injeta o nome do skill explicitamente** (não confia no LLM
  achar).

**Observação metodológica:** few-shot é o passo 1 de uma estratégia maior de
melhoria iterativa — antes de partir para fine-tuning ou RL, que exigem dataset
muito maior e infra adicional, fechamos o ciclo "edita skill → roda
`/evaluate/all` → mede delta" usando o próprio harness de avaliação.

**Arquivos:** `app/skills/*/SKILL.md`, `app/agents/recommender_agent.py`,
`app/services/refactor_service.py`, `app/core/prompts.py` (Critic).

---

### 16 · Skills substituem RAG (decisão arquitetural)

**Antes:** o conhecimento canônico de cada pattern vivia em
`app/knowledge/patterns/*.md` (5 arquivos) indexados em **PgVector** com
embeddings **HuggingFace** (`BAAI/bge-small-en-v1.5`, 384 dims) via Inference
API gratuita. O Recommender chamava `KnowledgeTools(knowledge=...)` para fazer
retrieval semântico.

**Agora:** o conhecimento vive em `app/skills/*/SKILL.md` (mesmo conteúdo,
formato Agno Skill). O Recommender chama `get_skill_instructions(name=...)` —
nome resolvido deterministicamente pelo serviço.

**O que mudou na prática:**

| Aspecto | RAG (antes) | Skills (agora) |
|---|---|---|
| Recuperação | Top-k semântico via embeddings | Lookup por nome — sem aproximação |
| Infra | PgVector + HuggingFace Inference API | Filesystem local |
| Variáveis de ambiente | `HUGGINGFACE_API_KEY`, `EMBEDDING_MODEL_ID`, `KNOWLEDGE_TABLE`, `PATTERNS_DIR` | (nenhuma adicional) |
| Dependências Python | `huggingface-hub`, `pgvector` | (nenhuma adicional) |
| Endpoint de boot | `POST /api/v1/knowledge/sync` (indexava no pgvector) | (removido — nada a sincronizar) |
| Determinismo | Top-k pode retornar variações | 1 skill, 1 arquivo, sempre o mesmo |

**Por que faz sentido para este projeto:**
1. **Espaço fechado de 5 patterns.** Top-k semântico só ajuda quando há
   ambiguidade na query — aqui o smell mapeia 1-pra-1 pro pattern, então o
   "nome do skill" é determinístico. Embeddings adicionam ruído sem upside.
2. **Conteúdo procedural, não factual.** Skills foram desenhadas exatamente
   pra "playbook de como aplicar X". RAG é melhor pra "tenho 10k docs e preciso
   achar os 3 relevantes" — não é o nosso caso.
3. **Reprodutibilidade acadêmica.** Pgvector + HF Inference API tem chance
   não-zero de variação entre runs (modelo de embedding, ranking). Skills são
   100% reproduzíveis — basta `git checkout`.
4. **Remove dependências.** Saíram `huggingface-hub`, `pgvector` e a
   exigência de token HF no `.env`. Em seguida, em um segundo passo (commit
   à parte), também caiu o `PostgresDb` — os agentes são stateless por
   chamada, então `db=` no `Agent(...)` ficou `None`, e `psycopg` +
   `sqlalchemy` saíram do `pyproject.toml`. A stack final só precisa de
   `MISTRAL_API_KEY`.

**O que foi apagado:**
- `app/knowledge/` (diretório inteiro: `provider.py` + `patterns/*.md`)
- `app/services/knowledge_service.py`
- `app/api/controllers/knowledge_controller.py`
- Rota `POST /api/v1/knowledge/sync` em `app/api/routes.py`
- Settings `huggingface_api_key`, `embedding_model_id`, `knowledge_table`, `patterns_dir`
- Tools mortos `design_pattern_reference_tool` e `smell_to_pattern_tool`
  (eram `@tool` wrappers de `lookup_pattern` / `resolve_pattern_for_smell` —
  as funções puras ficaram, são usadas pelo dataset integrity test)

**Tradeoff assumido:** perdemos a flexibilidade de retrieval semântico. Se o
projeto crescer para >20 patterns ou começar a aceitar smells fora da lista
fechada, o RAG volta a fazer sentido — mas até lá, skills são o caminho mais
enxuto.

**Arquivos:** `app/skills/`, `app/agents/recommender_agent.py`,
`app/services/refactor_service.py`, `app/core/config.py`, `pyproject.toml`,
`.env.example`.

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
| **8 · Memory Management** | Pipeline stateless por arquivo. Conhecimento de patterns é injetado via Agno Skills (lazy-load por nome), não há retrieval/memória de longo prazo. |
| **9 · Learning and Adaptation** | Fora do escopo acadêmico (sem RL/fine-tuning). |
| **10 · MCP** | Overhead de infraestrutura sem ganho — todas as tools são internas ao projeto. |
| **13 · HITL** | Os endpoints `/evaluate/*` contra ground truth substituem supervisão humana para fins acadêmicos. |
| **16 · Resource-Aware Optimization** | Modelo único (Llama 3.3 70B). Roteamento Flash/Pro não se aplica. |
| **17 · Reasoning Techniques (CoT/ToT/ReAct)** | Llama 3.3 já aplica CoT implícito; ReAct é contraditório com pipeline determinístico. |
| **20 · Prioritization** | Uma tarefa por vez, sem fila concorrente de objetivos. |

> **Nota sobre Team (Agno):** O `agno.Team` foi avaliado e descartado — veja `docs/architecture.md`
> para a justificativa detalhada. Em resumo: o Team usa um LLM como orquestrador, o que quebra
> o determinismo do pipeline e impede medir cada estágio individualmente para os endpoints `/evaluate/*`.
