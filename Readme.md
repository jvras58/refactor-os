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
├── api/                           # FastAPI: /detect /refactor /evaluate/(detector|refactor|critic|all) /knowledge/sync
├── agents/                        # Detector, Recommender, Critic
├── core/                          # config, prompts, schemas (Pydantic)
├── db/session.py                  # PostgresDb compartilhado (Agno)
├── knowledge/                     # PgVector + 5 .md (1 por pattern)
├── services/                      # refactor / evaluation / quality_checks / knowledge loader
├── tools/                         # ast, pattern_registry, diff, syntax
├── templates/                     # dashboard.html (Jinja2)
└── main.py                        # FastAPI ASGI entry point
dataset/
├── examples/                      # 10 programas COM bad smell (2 por categoria)
├── clean/                         # 10 programas limpos (medem Falsos Positivos)
├── solutions/                     # correct/ (10) + incorrect/ (10) — avaliam o Revisor
├── ground_truth.json              # gabarito do Detector (10 smell + 10 limpos)
├── critic_truth.json              # gabarito do Critic (10 corretas + 10 com defeito)
└── reports/                       # evaluation.{md,json} gerados pela avaliação
scripts/
└── run_evaluation.py              # CLI de avaliação (tabelas + relatório md/json)
tests/                             # unit tests determinísticos (tools + métricas + dataset)
```

## Setup

Os agentes usam **Mistral** como provider de LLM. Você precisa de uma
chave de API gratuita do Mistral:

1. Crie uma conta em [console.mistral.ai](https://console.mistral.ai).
2. Em **API Keys** gere uma nova chave (formato `oj2Z...`).
3. Cole no `.env` como `MISTRAL_API_KEY=oj2Z...`.

Para a base de conhecimento, usamos **HuggingfaceCustomEmbedder**
(BAAI/bge-small-en-v1.5, 384 dims) via **HF Inference API** gratuita
— sem compilacao Rust, sem provedor pago. Crie um token gratuito em
https://huggingface.co/settings/tokens e adicione no `.env` como
`HUGGINGFACE_API_KEY=hf_...`.

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

### Avaliação com código submetido (ad-hoc)

Os endpoints por agente (`/evaluate/detector`, `/evaluate/refactor`, `/evaluate/critic`)
têm **comportamento dual**:

- **Body vazio** → roda sobre o dataset fixo (comportamento padrão, igual ao anterior).
- **Body com `samples`** → roda sobre as amostras rotuladas enviadas, devolvendo as mesmas
  métricas (matriz de confusão, precision/recall/F1, per_file) calculadas só sobre o
  que foi enviado.

O rótulo esperado é **obrigatório** em cada amostra — sem ele não há como computar
TP/FP/TN/FN; payloads sem rótulo retornam `422`.

#### Schema das amostras

| Endpoint | Campos por amostra |
|---|---|
| `/evaluate/detector` | `source_code`, `expected_smell`, `name?`, `expected_pattern?` |
| `/evaluate/refactor` | `source_code`, `expected_pattern`, `name?`, `expected_smell?` |
| `/evaluate/critic`   | `problem_code`, `solution_code`, `applied_pattern`, `expected_approved`, `name?`, `defect_kind?` |

Valores aceitos para `expected_smell`: `Complex/Long Switch Statements`, `Long Parameter List`,
`God Class`, `Tight Coupling`, `Duplicated Code`, `No Smell Detected`.

Valores aceitos para `expected_pattern`/`applied_pattern`: `Strategy Pattern`,
`Builder/Parameter Object`, `Facade/SRP`, `Dependency Injection`, `Template Method`, `None`.

#### Exemplos

```bash
# Detector — mistura amostras com e sem smell para medir FP/FN
curl -X POST http://localhost:8000/api/v1/evaluate/detector \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {
        "name": "meu_god_class",
        "source_code": "class Big:\n    def m1(self): ...\n    def m2(self): ...\n",
        "expected_smell": "God Class"
      },
      {
        "name": "meu_codigo_limpo",
        "source_code": "def add(a, b):\n    return a + b\n",
        "expected_smell": "No Smell Detected"
      }
    ]
  }'

# Refatorador — cada amostra é um problema rotulado com o pattern esperado
curl -X POST http://localhost:8000/api/v1/evaluate/refactor \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {
        "name": "switch_grande",
        "source_code": "def calc(op, a, b):\n    if op == \"sum\": return a+b\n    elif op == \"sub\": return a-b\n",
        "expected_pattern": "Strategy Pattern"
      }
    ]
  }'

# Revisor — problema original + solução proposta + veredito esperado
curl -X POST http://localhost:8000/api/v1/evaluate/critic \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {
        "name": "solucao_correta",
        "problem_code": "class Big:\n    def m1(self): ...\n",
        "solution_code": "class Big:\n    def m1(self): ...\n",
        "applied_pattern": "Facade/SRP",
        "expected_approved": true
      }
    ]
  }'
```

#### Como testar

```bash
# 1. Testes unitários determinísticos (sem LLM) — cobrem os dois caminhos
uv run pytest tests/test_evaluation_metrics.py -v
#   test_evaluate_detector_dataset_path_still_works   → regressão do modo dataset
#   test_detector_evaluates_submitted_samples         → modo ad-hoc do Detector
#   test_refactor_evaluates_submitted_samples         → modo ad-hoc do Refatorador
#   test_critic_evaluates_submitted_samples           → modo ad-hoc do Revisor

# 2. Smoke test ao vivo (precisa de MISTRAL_API_KEY no .env)
docker compose up -d postgres
uv run uvicorn app.main:app --reload

# em outro terminal — payload sem rótulo deve falhar com 422
curl -i -X POST http://localhost:8000/api/v1/evaluate/detector \
  -H "Content-Type: application/json" \
  -d '{"samples":[{"source_code":"x=1"}]}'

# payload completo deve retornar DetectorMetrics com per_file=[...]
curl -s -X POST http://localhost:8000/api/v1/evaluate/detector \
  -H "Content-Type: application/json" \
  -d '{"samples":[{"name":"limpo","source_code":"def add(a,b): return a+b\n","expected_smell":"No Smell Detected"}]}' \
  | python -m json.tool
```

O endpoint agregado `/evaluate/all` continua **somente** sobre o dataset fixo — ad-hoc só
vale para os três endpoints por agente.

## Tests

```bash
uv run pytest
```

Cobertura: tools determinísticas (AST, diff, pattern registry, syntax). Os agentes em si
são testados via dataset de avaliação (não via mocks, conforme metodologia acadêmica).
