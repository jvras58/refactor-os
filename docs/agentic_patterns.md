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
| 14 | **Skills + RAG (lado a lado)** | `agno.skills.Skills(loaders=[LocalSkills("app/skills")])` injetado no Recommender (estrutura canônica via `get_skill_instructions`) **e** agentic RAG nativo (`Agent(knowledge=get_solution_knowledge(), search_knowledge=True)`) sobre PgVector (exemplos via `search_knowledge_base`). Ver §15 e §16. |
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

### 16 · RAG (PgVector) + corpus de soluções

**Decisão:** Skills e RAG coexistem com papéis distintos:

| Camada | Papel | Onde |
|---|---|---|
| **Skills** | Playbook procedural ("como aplicar o pattern X") + 1 exemplo canônico, lookup por nome | `app/skills/*/SKILL.md` |
| **RAG (PgVector)** | Recuperação semântica de exemplos problema→refatoração análogos | `app/knowledge/solutions/*.md` |

A estrutura canônica de cada pattern fica **só** nas Skills; o RAG indexa **só** o
corpus de soluções (sem duplicar a estrutura nem o registry — que foi removido).

**Componentes:**
- `app/db/session.py` + `db=get_db()` nos 3 agentes (Postgres como `contents_db`).
- `app/knowledge/provider.py`: `get_solution_knowledge()` (PgVector + HuggingFace
  embeddings, `BAAI/bge-small-en-v1.5`, 384 dims) e `sync_knowledge()`.
- **Corpus** `app/knowledge/solutions/*.md` — 5 exemplos autorais problema→solução,
  **deliberadamente distintos de `dataset/`** para não vazar ground truth na avaliação
  do Critic (que consome `dataset/solutions/`).
- O Recommender usa agentic RAG nativo: `Agent(knowledge=get_solution_knowledge(),
  search_knowledge=True)` registra a tool `search_knowledge_base` (instruída também no
  prompt); as Skills seguem via `get_skill_instructions`.
- Endpoint `POST /api/v1/knowledge/sync` ([knowledge_controller.py](../app/api/controllers/knowledge_controller.py)):
  upsert idempotente do corpus no índice pgvector.
- Deps de runtime: `sqlalchemy`, `psycopg[binary]`, `pgvector`, `huggingface-hub`.

**Pré-requisitos para o RAG funcionar:** Postgres no ar (`docker compose up -d postgres`),
`HUGGINGFACE_API_KEY` no `.env`, e uma chamada a `/knowledge/sync` para popular a tabela
(a tabela nasce vazia). Validado: `sync` indexa `{solutions: 5}` e o retrieval retorna o
doc correto por similaridade.

**Tradeoff assumido:** custo de infra (Postgres + token HF + passo de sync) em troca de um
corpus de soluções recuperável semanticamente; o playbook fixo do pattern segue nas Skills.

**Arquivos:** `app/db/session.py`, `app/knowledge/provider.py`,
`app/knowledge/solutions/*.md`, `app/api/controllers/knowledge_controller.py`,
`app/api/routes.py`, `app/core/config.py`, `compose.yml`, `pyproject.toml`, `.env.example`.

---

### 17 · Matriz heurística como prior determinístico do Detector

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
| **8 · Memory Management** | Sem memória de sessão/conversa entre requests. Há **retrieval** de conhecimento (Skills por nome + RAG semântico via PgVector — ver §16), mas nenhuma memória de longo prazo do usuário ou histórico de turnos. |
| **9 · Learning and Adaptation** | Fora do escopo acadêmico (sem RL/fine-tuning). |
| **10 · MCP** | Overhead de infraestrutura sem ganho — todas as tools são internas ao projeto. |
| **13 · HITL** | Os endpoints `/evaluate/*` contra ground truth substituem supervisão humana para fins acadêmicos. |
| **16 · Resource-Aware Optimization** | Modelo único (Llama 3.3 70B). Roteamento Flash/Pro não se aplica. |
| **17 · Reasoning Techniques (CoT/ToT/ReAct)** | Llama 3.3 já aplica CoT implícito; ReAct é contraditório com pipeline determinístico. |
| **20 · Prioritization** | Uma tarefa por vez, sem fila concorrente de objetivos. |

> **Nota sobre Team (Agno):** O `agno.Team` foi avaliado e descartado — veja `docs/architecture.md`
> para a justificativa detalhada. Em resumo: o Team usa um LLM como orquestrador, o que quebra
> o determinismo do pipeline e impede medir cada estágio individualmente para os endpoints `/evaluate/*`.
