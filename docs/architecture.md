# Arquitetura — Como os Agentes se Conectam

Este documento descreve o fluxo de execução do pipeline multi-agente determinístico
do `refactor-os`.

## Visão geral

```
┌──────────────────┐   DetectionScanResult   ┌──────────────────┐
│  Multi-Detector  ├────────────────────────►│   Recommender    │
│  (8 checagens)   │   (alvo selecionado)    │      Agent       │
└──────────────────┘                         └──────────┬───────┘
       ▲                                                │
       │                                                │ RefactoringProposal
       │                                                ▼
       │                                      ┌──────────────────┐
       │                                      │   Critic Agent   │
       │                                      │   (Reflection)   │
       │                                      └────────┬─────────┘
       │                                               │
       │        ReflectionReview (is_approved=False)   │
       └────── feedback (até MAX_REFLECTION_ITERATIONS) ┘
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
| Detecção          | `app/services/multi_detector_service.py` | Pipeline multi-label de 4 fases (validação → heurística → 8 checagens LLM → compilação). |
| Agente            | `app/agents/*_agent.py`            | Factories que constroem cada `Agent` da Agno.                      |
| LLM               | `app/core/llm.py`                  | `build_main_model()` (tool/skill calling) + `build_parser_model()` (extração de JSON). |
| Tools             | `app/tools/*.py`                   | Funções determinísticas (matriz heurística, diff, syntax, logic signals). |
| Schemas           | `app/core/schemas.py`              | Contratos Pydantic + enums `SmellType`/`PatternType` + mapeamento `SMELL_TO_PATTERN`. |
| Exceptions        | `app/core/exceptions.py`           | `InvalidPythonCodeError` (fase 1 do detector).                     |
| Skills            | `app/skills/<pattern>/SKILL.md`    | Skills Agno (1 por design pattern) — conhecimento canônico carregado sob demanda pelo Recommender via `get_skill_instructions`. |
| Utils             | `app/utils/retry.py`               | `arun_with_backoff` (429s) + `arun_typed` (retry quando parser_model devolve string crua). |

## Como cada agente é construído

Cada factory injeta:
- `model` via `build_main_model()` — Mistral configurado para tool/skill calling.
- `parser_model` via `build_parser_model()` — Mistral em temperatura 0, sem tools, só para extrair o `output_schema`.
- `tools` ou `skills` específicas do papel (o Detector não usa tools — a heurística roda fora do Agno).
- `instructions` do `app/core/prompts.py`.
- `output_schema` Pydantic (Spec-Driven).

O Detector é stateless e sem `db=` — cada chamada é um julgamento sim/não isolado.

```python
# app/agents/detector_agent.py (resumo)
return Agent(
    id="detector-agent",
    model=build_main_model(),
    parser_model=build_parser_model(),
    instructions=TYPE_DETECTOR_INSTRUCTIONS,   # genérico: o tipo vem no prompt por chamada
    output_schema=TypeDetectionResult,         # veredito de UM tipo por chamada
)
```

## Conexão entre os agentes (fluxo passo a passo)

A cola entre os agentes é o `RefactorService` — **não** um `Team` da Agno. Isso é
intencional: o projeto exige um pipeline determinístico onde cada estágio é
mensurável de forma independente.

### 1. `service.detect(source_code)` — multi-detector em 4 fases
Delegado ao `MultiDetectorService`:
1. **Validação** — `ast.parse`; código inválido levanta `InvalidPythonCodeError`
   (a API devolve `422`).
2. **Heurística** — `score_all_smells()` produz um `SmellHeuristicSignal` por smell
   (sempre os 4, mesmo sem evidência).
3. **8 chamadas LLM** — uma por tipo (4 smells + 4 patterns). Cada chamada recebe a
   definição do tipo + o prior heurístico relevante e devolve um `TypeDetectionResult`
   (detected + evidências + reasoning). O prior informa, mas nunca pula uma checagem.
4. **Compilação** — estratégia trocável (`ResultCompiler`); a padrão devolve a lista
   de nomes detectados (mesmo formato do `problems` do ground truth).

Retorna `DetectionScanResult` (heurística + os 8 vereditos).

### 2. Seleção do alvo — `RefactorService._select_target(scan)`
O scan é multi-label, mas o Recommender refatora **um** problema por vez:
- se algum **smell** foi detectado → escolhe o de maior score heurístico; o pattern
  vem de `SMELL_TO_PATTERN[smell]`;
- senão, se algum **pattern** foi detectado como aplicável → usa esse pattern
  (o smell relacionado vem de `PATTERN_TO_SMELL`);
- senão → pipeline encerra sem proposta (`approved=False, iterations=0`).

### 3. `service.propose(source_code, target_smell, target_pattern, detection, prior_critique=None)`
- Resolve o nome do skill via `_PATTERN_TO_SKILL[target_pattern]`.
- Constrói o prompt incluindo: o smell alvo, o pattern obrigatório, o
  **skill obrigatório**, o reasoning e as evidências do Detector e
  (se houver) a crítica da iteração anterior.
- Chama `recommender_agent.arun(prompt)`.
- O Recommender é instruído a chamar `get_skill_instructions(name="<skill>")`
  para carregar a estrutura canônica + exemplo do pattern antes de propor o
  código. O `Skills(loaders=[LocalSkills("app/skills")])` é injetado pela
  factory do agente.
- Retorna `RefactoringProposal`.

### 4. `service.review(source_code, proposal)`
- Constrói o prompt comparando original × refatorado + o prior de preservação
  de lógica (`logic_signals`).
- Chama `critic_agent.arun(prompt)`.
- O Critic usa `syntax_checker_tool` (ast.parse + ruff) e `diff_generator_tool`.
- Retorna `ReflectionReview` com `is_approved` e (opcional) `critique`.

### 5. Reflection loop
`RefactorService.run()` orquestra os passos acima dentro de um for loop
limitado por `settings.max_reflection_iterations` (default 3):

```python
scan = await self.detect(source_code)              # multi-label
target_smell, target_pattern, detection = self._select_target(scan)
if target_smell is None:
    return RefactorResult(detection=scan, approved=False, iterations=0)

for iteration in range(1, max_iter + 1):
    proposal = await self.propose(source, target_smell, target_pattern, detection, prior_critique=critique)
    review = await self.review(source, proposal)
    if review.is_approved:
        return RefactorResult(approved=True, iterations=iteration, ...)
    critique = review.critique
return RefactorResult(approved=False, iterations=max_iter, ...)
```

## Schemas trocados (Spec-Driven)

```
RefactorRequest ──► Multi-Detector ──► DetectionScanResult ──► seleção do alvo
                                                                     │
                                     Recommender ◄───────────────────┘
                                          │
                        RefactoringProposal
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
- métricas isoladas por estágio (precision/recall multi-label do Detector vs. accuracy do
  Recommender+Critic),

um `Team` quebraria as três garantias. A própria documentação da Agno indica
**custom execution function** quando se precisa de "fine-grained control over the
orchestration logic" — exatamente o que `RefactorService.run()` faz.
