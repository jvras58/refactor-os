# refactor-os

Sistema multi-agente **determinístico** para revisão e refatoração de código orientada por
Design Patterns. Este projeto atua como um
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
├── api/                           # FastAPI: routes: /detect /refactor /evaluate /knowledge/sync
├── agents/                        # Detector, Recommender, Critic, Team
├── core/                          # config, prompts, schemas (Pydantic)
├── db/session.py                  # PostgresDb compartilhado (Agno)
├── knowledge/                     # PgVector + 5 .md (1 por pattern)
├── services/                      # refactor / evaluation / knowledge loader
├── tools/                         # ast, pattern_registry, diff, syntax
├── templates/                     # .html com o template engine (jinja2) da pagina de dashboard
└── main.py                        # FastAPI ASGI entry point
dataset/
├── examples/                      # 5 scripts seed (1 por smell)
└── ground_truth.json              # gabarito p/ Precision/Recall/Accuracy
tests/                             # unit tests determinísticos das tools
```

## Setup

Os agentes usam **Mistral** como provider de LLM. Você precisa de uma
chave de API gratuita do Mistral:

1. Crie uma conta em [console.mistral.ai](https://console.mistral.ai).
2. Em **API Keys** gere uma nova chave (formato `oj2Z...`).
3. Cole no `.env` como `MISTRAL_API_KEY=oj2Z...`.

```bash
cp .env.example .env
# preencha MISTRAL_API_KEY=oj2Z...

# instalar deps
uv sync --extra dev
```

Para trocar o modelo Mistral (ex.: `mistral-medium-latest`, `mistral-large-latest`),
ajuste `LLM_MODEL_ID` no `.env`.

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
- `POST /api/v1/evaluate` — relatório combinado legado (precision/recall/accuracy).
- `POST /api/v1/evaluate/detector` — **Agente Rastreador**: Falsos Positivos / Falsos Negativos.
- `POST /api/v1/evaluate/refactor` — **Agente Refatorador**: precisão/qualidade da solução.
- `POST /api/v1/evaluate/critic` — **Agente Revisor**: false accept / false reject.
- `POST /api/v1/evaluate/all` — os três relatórios de uma vez.
- `POST /api/v1/knowledge/sync` — indexa os 5 patterns no PgVector.
- `GET  /`          - health endpoint
- `GET  /dashboard` - Dashboard para uso do pepiline.

## Avaliação empírica

Três avaliações independentes, uma por agente (escopo 10 problemas + 10 soluções):

| Agente | Mede | Endpoint |
|---|---|---|
| **Rastreador** (Detector) | Falsos Negativos (deixou passar) e Falsos Positivos (viu onde não há) | `/evaluate/detector` |
| **Refatorador** (Recommender) | Pattern correto + sintaxe válida + API preservada | `/evaluate/refactor` |
| **Revisor** (Critic) | False Accept (aprovou incorreta) e False Reject (reprovou correta) | `/evaluate/critic` |

```bash
# 1. indexar a base de patterns
curl -X POST http://localhost:8000/api/v1/knowledge/sync

# 2a. via CLI — imprime tabelas e gera o relatório (.md auto-contido + .json)
uv run python scripts/run_evaluation.py --all --md dataset/reports/evaluation.md --json dataset/reports/evaluation.json

# 2b. via API — relatório completo
curl -X POST http://localhost:8000/api/v1/evaluate/all
```

O dataset (`dataset/README.md`) já traz os 10/10 de cada eixo; é só expandir se quiser mais.

## Tests

```bash
uv run pytest
```

Cobertura: tools determinísticas (AST, diff, pattern registry, syntax). Os agentes em si
são testados via dataset de avaliação (não via mocks, conforme metodologia acadêmica).
