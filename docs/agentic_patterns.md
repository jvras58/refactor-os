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
| 14 | **Skills + RAG (lado a lado)** | `agno.skills.Skills(loaders=[LocalSkills("app/skills")])` injetado no Recommender (uma `SKILL.md` por pattern via `get_skill_instructions`) **e** `KnowledgeTools(get_pattern_knowledge())` sobre PgVector. Ver §15 e §18 (RAG foi reintroduzido — §16/§17 estão **revertidas**). |
| 19 | **Evaluation and Monitoring** | Endpoints `/evaluate/{detector,refactor,critic,all}` — métricas independentes por agente contra `dataset/ground_truth.json` e `dataset/critic_truth.json` (ou amostras enviadas ad-hoc) |

> ⚠️ **Estado atual (branch `feat-dataset-matrix-evoluate`):** as decisões §16 (Skills
> substituem RAG) e §17 (sem Postgres) foram **revertidas**. O RAG via PgVector +
> Postgres voltou e ganhou um corpus de soluções, e o Detector passou a usar uma
> **matriz heurística** determinística como prior. Detalhes em §18 e §19 abaixo —
> §16/§17 ficam preservadas como registro histórico do que foi removido e por quê.

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

### 16 · Skills substituem RAG (decisão arquitetural) — ⚠️ REVERTIDA (ver §18)

> **Status:** revertida na branch `feat-dataset-matrix-evoluate`. O RAG via PgVector
> voltou e agora coexiste com as Skills (Skills para o playbook do pattern; RAG para
> recuperar exemplos do corpus de soluções). A seção abaixo permanece como registro
> da motivação original da remoção.

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

### 17 · Stateless agents (sem PostgresDb) — ⚠️ REVERTIDA (ver §18)

> **Status:** revertida na branch `feat-dataset-matrix-evoluate`. O `PostgresDb`
> voltou (`app/db/session.py`, `db=get_db()` nos 3 agentes) porque o RAG via PgVector
> precisa do Postgres e da `contents_db`. A seção abaixo permanece como registro da
> motivação original da remoção; o "quando reverter" no fim dela foi efetivamente acionado.

**Decisão:** os 3 agentes do pipeline são construídos **sem `db=`**. O Agno
aceita `Agent(model=..., parser_model=..., tools=..., output_schema=...)`
sem o parâmetro de banco, e quando isso acontece o agente fica stateless por
chamada — `agent.db` é `None` e nenhuma sessão/trace é persistida.

**Como verifiquei que era seguro remover:**

```
$ grep -rE 'session_id|add_history|memory|read_chat_history|enable_user_memories|enable_session_summaries' app/
(zero hits)
```

Nenhum lugar do código exercitava qualquer feature do Agno que dependa do `db`.
O `PostgresDb` antigo só servia ao RAG via `PgVector` — e o RAG já tinha saído
junto na §16 (skills substituíram o registry).

**Por que sessões/history/memory não trazem valor no nosso caso:**

| Feature do Agno | Pra que serve | Por que NÃO se aplica aqui |
|---|---|---|
| `session_id` + history persistido | Continuar uma conversa entre chamadas separadas (chatbot, assistente interativo). | Cada `POST /refactor` é atômico: recebe código, processa, devolve resultado. Não há continuidade entre requests. |
| `add_history_to_context=True` | Agente vê as N últimas mensagens do mesmo `session_id`. | A reflection loop **parece** multi-turno, mas é coordenada **em Python** pelo `RefactorService.run()` — quando o Critic reprova, a `critique` vai pro próximo prompt do Recommender como string injetada (via `prior_critique` em `refactor_service.py`). Garante (i) ordem fixa, (ii) número exato de iterações, (iii) cada estágio mensurável independente — as 3 garantias que motivaram não usar `Team` da Agno. |
| `enable_user_memories` (Mem0-like) | Extrair fatos persistentes sobre o usuário ("prefere TypeScript", "trabalha com Django"). | Não há "usuário" persistente — o cenário acadêmico processa arquivos do `dataset/` ou amostras ad-hoc enviadas via API. `RefactorRequest` nem tem `user_id`. |
| `enable_session_summaries` | Resumo automático ao final de sessão longa. | Sessão de 1 request não tem o que resumir. |
| Traces no DB | Observabilidade Agno-native em produção. | Não há produção. Os `logger.exception` / `logger.warning` em `RefactorService` + a saída do `/evaluate/all` (gera `evaluation.json` com per-file) já cobrem debug e medição. |

**Custo de manter um banco que não é usado:**
- Container Postgres no `compose.yml` + volume `pgdata`.
- Dependências `psycopg[binary]` e `sqlalchemy` no `pyproject.toml`.
- `DB_URL` no `.env` (mais um setup pra usuário acertar).
- `app/db/session.py` + `get_db()` espalhado em 3 factories.
- Avaliação fica menos reproduzível (rastros de runs anteriores no banco entre `pytest` consecutivos, a menos que alguém lembre de truncar tabelas).

**Quando reverter essa decisão:**

1. **UI interativa** onde usuário discute a refatoração em turnos ("não, prefere essa versão com dataclass" → agente lembra da iteração anterior) — aí `session_id` faz sentido.
2. **Auth/multi-usuário** com histórico por pessoa — aí `enable_user_memories` faz sentido.
3. **Observabilidade de produção** com tracing Agno-native em vez de só logs estruturados — aí o `db=` volta pra capturar runs.

Pra "sistema acadêmico stateless que avalia agentes em isolamento", **YAGNI**.
Se um dia o caso de uso mudar, ressuscita do `git log` (commit `b5e1d09^`).

**Arquivos afetados:** removido `app/db/session.py`, `db=get_db()` dos 3
agentes, `Settings.db_url`, `DB_URL` do `.env.example`, serviço `postgres` +
volume `pgdata` do `compose.yml`, deps `psycopg[binary]` e `sqlalchemy` do
`pyproject.toml`.

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

### 18 · RAG reintroduzido + corpus de soluções (reversão de §16/§17)

**Decisão:** na branch `feat-dataset-matrix-evoluate` o RAG via PgVector + Postgres
voltou e ganhou um segundo corpus. Skills e RAG passam a coexistir com papéis distintos:

| Camada | Papel | Onde |
|---|---|---|
| **Skills** | Playbook procedural ("como aplicar o pattern X"), lookup por nome | `app/skills/*/SKILL.md` |
| **RAG (PgVector)** | Recuperação semântica de exemplos de referência | `app/knowledge/patterns/*.md` + `app/knowledge/solutions/*.md` |

**O que foi (re)adicionado:**
- `app/db/session.py` + `db=get_db()` nos 3 agentes (Postgres como `contents_db`).
- `app/knowledge/provider.py`: `get_pattern_knowledge()` (PgVector + HuggingFace
  embeddings, `BAAI/bge-small-en-v1.5`, 384 dims) e `sync_knowledge()`.
- **Corpus novo** `app/knowledge/solutions/*.md` — 5 exemplos autorais problema→solução,
  **deliberadamente distintos de `dataset/`** para não vazar ground truth na avaliação
  do Critic (que consome `dataset/solutions/`).
- Endpoint `POST /api/v1/knowledge/sync` ([knowledge_controller.py](../app/api/controllers/knowledge_controller.py)):
  upsert idempotente dos dois corpora no índice pgvector.
- Deps de runtime: `sqlalchemy`, `psycopg[binary]`, `pgvector`, `huggingface-hub`.

**Pré-requisitos para o RAG funcionar:** Postgres no ar (`docker compose up -d postgres`),
`HUGGINGFACE_API_KEY` no `.env`, e uma chamada a `/knowledge/sync` para popular a tabela
(a tabela nasce vazia). Validado: `sync` indexa `{patterns: 5, solutions: 5}` e o retrieval
retorna o doc correto por similaridade.

**Tradeoff assumido:** reintroduz a infra (Postgres + token HF + passo de sync) que §16/§17
haviam removido em nome da reprodutibilidade. A justificativa é o corpus de soluções
recuperável semanticamente; o playbook fixo do pattern segue nas Skills.

**Arquivos:** `app/db/session.py`, `app/knowledge/provider.py`,
`app/knowledge/solutions/*.md`, `app/api/controllers/knowledge_controller.py`,
`app/api/routes.py`, `app/core/config.py`, `compose.yml`, `pyproject.toml`, `.env.example`.

---

### 19 · Matriz heurística como prior determinístico do Detector

**Problema resolvido:** o Detector julgava o smell a partir de métricas cruas devolvidas
por `ast_analyzer_tool`, deixando toda a classificação a cargo do LLM (probabilístico).

**Implementação:** [`app/tools/heuristic_engine.py`](../app/tools/heuristic_engine.py) —
uma matriz determinística que parseia o AST e **ranqueia os 5 smells do escopo** por sinais
estruturais explícitos:

| Smell | Sinal heurístico |
|---|---|
| Complex/Long Switch | ramos de `if/elif` ou `match/case` ≥ 3 |
| Long Parameter List | função com ≥ 5 parâmetros |
| God Class | classe com > 20 membros (métodos + atributos `self.`) |
| Tight Coupling | colaborador concreto instanciado dentro da classe (`self.x = Mod.Foo(...)`) |
| Duplicated Code | mesmo método substancial reimplementado em ≥ 2 classes irmãs |

`RefactorService.detect()` calcula `score_smells()` **fora do Agno** e injeta o resultado
ranqueado no prompt como "Prior da matriz heurística". O LLM **confirma ou refuta** o
candidato de maior score e produz o `reasoning` explicável — o prior não decide sozinho
(decisão "prior + LLM confirma", não "Detector 100% determinístico").

**Resultado:** 10/10 de type-accuracy e 0 falsos positivos sobre o dataset rotulado
(20 arquivos), travado em [`tests/test_heuristic_engine.py`](../tests/test_heuristic_engine.py).

> **TODO (futuro):** remover `ast_analyzer_tool` do Detector. Com o prior heurístico
> injetado no prompt, o tool ficou redundante — ele reparseia o mesmo AST que a matriz
> já analisou. Antes de remover: confirmar que nenhum critério de avaliação depende do
> tool ser chamado e ajustar `DETECTOR_INSTRUCTIONS` ([prompts.py](../app/core/prompts.py))
> que hoje ainda manda "SEMPRE chame `ast_analyzer_tool`".

**Arquivos:** `app/tools/heuristic_engine.py`, `app/services/refactor_service.py`,
`app/core/prompts.py`, `tests/test_heuristic_engine.py`.

---

## Patterns Descartados (e por quê)

| Pattern | Motivo do descarte |
|---------|-------------------|
| **2 · Routing** | Só há 5 smells e o Detector já classifica — um router seria duplicação. |
| **3 · Parallelization** | Fluxo é sequencial por dependência de dados (saída de cada estágio é input do próximo). |
| **6 · Planning** | Escopo fixo (5 patterns, 1 refactor por arquivo). Não há plano multi-etapa a formular. |
| **8 · Memory Management** | Sem memória de sessão/conversa entre requests. Há **retrieval** de conhecimento (Skills por nome + RAG semântico via PgVector — ver §18), mas nenhuma memória de longo prazo do usuário ou histórico de turnos. |
| **9 · Learning and Adaptation** | Fora do escopo acadêmico (sem RL/fine-tuning). |
| **10 · MCP** | Overhead de infraestrutura sem ganho — todas as tools são internas ao projeto. |
| **13 · HITL** | Os endpoints `/evaluate/*` contra ground truth substituem supervisão humana para fins acadêmicos. |
| **16 · Resource-Aware Optimization** | Modelo único (Llama 3.3 70B). Roteamento Flash/Pro não se aplica. |
| **17 · Reasoning Techniques (CoT/ToT/ReAct)** | Llama 3.3 já aplica CoT implícito; ReAct é contraditório com pipeline determinístico. |
| **20 · Prioritization** | Uma tarefa por vez, sem fila concorrente de objetivos. |

> **Nota sobre Team (Agno):** O `agno.Team` foi avaliado e descartado — veja `docs/architecture.md`
> para a justificativa detalhada. Em resumo: o Team usa um LLM como orquestrador, o que quebra
> o determinismo do pipeline e impede medir cada estágio individualmente para os endpoints `/evaluate/*`.
