# Arquitetura — Como os Agentes se Conectam

Este documento descreve o fluxo de execução do pipeline multi-agente determinístico
do `refactor-os`.

## Visão geral

```
┌──────────────┐    SmellDetection      ┌──────────────────┐
│   Detector   ├───────────────────────►│   Recommender    │
│    Agent     │                        │      Agent       │
└──────────────┘                        └──────────┬───────┘
       ▲                                            │
       │                                            │ RefactoringProposal
       │                                            ▼
       │                                  ┌──────────────────┐
       │                                  │   Critic Agent   │
       │                                  │   (Reflection)   │
       │                                  └────────┬─────────┘
       │                                           │
       │      ReflectionReview (is_approved=False) │
       └────── feedback (até MAX_REFLECTION_ITERATIONS) ──┘
                                                   │
                                        is_approved=True
                                                   ▼
                                            RefactorResult
```

## Componentes

| Camada            | Caminho                            | Responsabilidade                                                   |
|-------------------|------------------------------------|--------------------------------------------------------------------|
| API               | `app/api/routes.py`                | Endpoints FastAPI (`/detect`, `/refactor`, `/evaluate/{detector,refactor,critic,all}`). |
| Service           | `app/services/refactor_service.py` | Orquestra a pipeline determinística com reflection loop.           |
| Agente            | `app/agents/*_agent.py`            | Factories que constroem cada `Agent` da Agno (stateless — sem `db=`).|
| LLM               | `app/core/llm.py`                  | `build_main_model()` (tool/skill calling) + `build_parser_model()` (extração de JSON). |
| Tools             | `app/tools/*.py`                   | Funções determinísticas (AST, diff, syntax).                       |
| Schemas           | `app/core/schemas.py`              | Contratos Pydantic trocados entre os agentes + mapeamento `SMELL_TO_PATTERN`.|
| Skills            | `app/skills/<pattern>/SKILL.md`    | 5 skills Agno (1 por design pattern) — conhecimento canônico carregado sob demanda pelo Recommender via `get_skill_instructions`. Substitui o antigo RAG via PgVector. |
| Utils             | `app/utils/retry.py`               | `arun_with_backoff` (429s) + `arun_typed` (retry quando parser_model devolve string crua). |

## Como cada agente é construído

Cada factory injeta:
- `model` via `build_main_model()` — Mistral configurado para tool/skill calling.
- `parser_model` via `build_parser_model()` — Mistral em temperatura 0, sem tools, só para extrair o `output_schema`.
- `tools` ou `skills` específicas do papel.
- `instructions` do `app/core/prompts.py`.
- `output_schema` Pydantic (Spec-Driven).

Nenhum agente recebe `db=` — o pipeline é stateless por requisição.

```python
# app/agents/detector_agent.py (resumo)
return Agent(
    id="detector-agent",
    model=build_main_model(),
    parser_model=build_parser_model(),
    tools=[ast_analyzer_tool],
    instructions=DETECTOR_INSTRUCTIONS,
    output_schema=SmellDetection,
)
```

## Conexão entre os agentes (fluxo passo a passo)

A cola entre os agentes é o `RefactorService` — **não** um `Team` da Agno. Isso é
intencional: o projeto exige um pipeline determinístico onde cada estágio é
mensurável de forma independente.

### 1. `service.detect(source_code)`
- Constrói o prompt com o código original.
- Chama `detector_agent.run(prompt)`.
- O Detector usa a tool `ast_analyzer_tool` (radon + AST) para identificar o smell.
  O `source_code` é inlinado direto no prompt — não há leitura de filesystem.
- Retorna `SmellDetection` (Pydantic, validado por `output_schema`).

### 2. `service.propose(source_code, detection, prior_critique=None)`
- Resolve o pattern obrigatório via `SMELL_TO_PATTERN[smell_type]` e o nome do
  skill correspondente via `_PATTERN_TO_SKILL[expected_pattern]`.
- Constrói o prompt incluindo: o smell detectado, o pattern obrigatório, o
  **skill obrigatório**, a justificativa do Detector, as linhas afetadas e
  (se houver) a crítica da iteração anterior.
- Chama `recommender_agent.run(prompt)`.
- O Recommender é instruído a chamar `get_skill_instructions(name="<skill>")`
  para carregar a estrutura canônica + exemplo do pattern antes de propor o
  código. O `Skills(loaders=[LocalSkills("app/skills")])` é injetado pela
  factory do agente.
- Retorna `RefactoringProposal`.

### 3. `service.review(source_code, proposal)`
- Constrói o prompt comparando original × refatorado.
- Chama `critic_agent.run(prompt)`.
- O Critic usa `syntax_checker_tool` (ast.parse + ruff) e `diff_generator_tool`.
- Retorna `ReflectionReview` com `is_approved` e (opcional) `critique`.

### 4. Reflection loop
`RefactorService.run()` orquestra os 3 passos acima dentro de um for loop
limitado por `settings.max_reflection_iterations` (default 3):

```python
for iteration in range(1, max_iter + 1):
    proposal = self.propose(source_code, detection, prior_critique=critique)
    review = self.review(source_code, proposal)
    if review.is_approved:
        return RefactorResult(approved=True, iterations=iteration, ...)
    critique = review.critique
return RefactorResult(approved=False, iterations=max_iter, ...)
```

## Schemas trocados (Spec-Driven)

```
RefactorRequest ──► Detector ──► SmellDetection ──► Recommender
                                                        │
                            RefactoringProposal ◄───────┘
                                    │
                                    ▼
                                 Critic ──► ReflectionReview
                                                │
                                                ▼
                                          RefactorResult
```

Todos definidos em `app/core/schemas.py` e validados automaticamente pela Agno via
o parâmetro `output_schema` de cada `Agent`.

## Por que NÃO usamos `Team` da Agno

Os modos `route` e `coordinate` introduzem um **LLM coordenador** acima dos agentes.
Para um pipeline cirúrgico com:
- ordem fixa Detector→Recommender→Critic,
- número exato de iterações de reflection,
- métricas isoladas por estágio (precision/recall do Detector vs. accuracy do
  Recommender+Critic),

um `Team` quebraria as três garantias. A própria documentação da Agno indica
**custom execution function** quando se precisa de "fine-grained control over the
orchestration logic" — exatamente o que `RefactorService.run()` faz.
