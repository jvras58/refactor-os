# refactor-os

Sistema multi-agente **determinístico** para revisão e refatoração de código orientada por
Design Patterns. Diferente de assistentes de chat genéricos, este projeto atua como um
**pipeline cirúrgico** restrito a 5 pares Smell↔Pattern, com etapa explícita de Reflection.

## Escopo (5 Smells × 5 Patterns)

| Bad Smell                          | Design Pattern             |
|-----------------------------------|----------------------------|
| Complex/Long Switch Statements    | Strategy Pattern           |
| Long Parameter List               | Builder/Parameter Object   |
| God Class                         | Facade/SRP                 |
| Tight Coupling                    | Dependency Injection       |
| Duplicated Code                   | Template Method            |

## Pipeline

```
Detector ──► Recommender ──► Critic ──► (aprovado) ──► resultado
                  ▲                │
                  └── Reflection ◄─┘  (até 3 iterações)
```

- **Detector Agent**: AST + radon → identifica o smell e linhas afetadas (`SmellDetection`).
- **Recommender Agent**: consulta o registro estrito de patterns + KnowledgeBase (PgVector) → propõe `RefactoringProposal`.
- **Critic Agent (Reflection)**: valida sintaxe (ruff/ast) + diff + preservação de lógica (`ReflectionReview`).

Comunicação **Spec-Driven** via Pydantic em `app/core/schemas.py`.

## Arquitetura

```
app/
├── api/routes.py                 # FastAPI: /detect /refactor /evaluate /knowledge/sync
├── agents/                        # Detector, Recommender, Critic, Team
├── core/                          # config, prompts, schemas (Pydantic)
├── db/session.py                  # PostgresDb compartilhado (Agno)
├── knowledge/                     # PgVector + 5 .md (1 por pattern)
├── services/                      # refactor / evaluation / knowledge loader
├── tools/                         # ast, pattern_registry, diff, syntax
└── main.py                        # AgentOS + FastAPI ASGI
dataset/
├── examples/                      # 5 scripts seed (1 por smell)
└── ground_truth.json              # gabarito p/ Precision/Recall/Accuracy
tests/                             # unit tests determinísticos das tools
```

## Setup

```bash
cp .env.example .env
# preencha OPENAI_API_KEY=...

# instalar deps
uv sync --extra dev
```

## Executar

### Local
```bash
docker compose up -d postgres        # sobe pgvector na porta 5532
uv run uvicorn app.main:app --reload
```

### Docker (stack completa)
```bash
docker compose up --build
```

## Endpoints

- `POST /api/v1/detect` — apenas o Detector.
- `POST /api/v1/refactor` — pipeline completo Detector → Recommender → Critic com reflection loop.
- `POST /api/v1/evaluate` — roda o dataset e retorna métricas (precision/recall/accuracy).
- `POST /api/v1/knowledge/sync` — indexa os 5 patterns no PgVector.
- `GET  /api/v1/health`.

## Avaliação empírica

```bash
# 1. indexar a base de patterns
curl -X POST http://localhost:8000/api/v1/knowledge/sync
# 2. rodar avaliação contra o ground truth
curl -X POST http://localhost:8000/api/v1/evaluate
```

Métricas reportadas: **Detector Precision**, **Detector Recall**, **Refactor Accuracy**.
Expanda o dataset para 20 scripts seguindo `dataset/README.md`.

## Tests

```bash
uv run pytest
```

Cobertura: tools determinísticas (AST, diff, pattern registry, syntax). Os agentes em si
são testados via dataset de avaliação (não via mocks, conforme metodologia acadêmica).
