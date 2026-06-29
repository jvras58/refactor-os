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

- **Detector Agent**: uma **matriz heurística** (AST determinístico) ranqueia os smells prováveis e injeta esse *prior* no prompt; o LLM confirma/refuta e explica (`SmellDetection`).
- **Recommender Agent**: carrega o `SKILL.md` do pattern obrigatório via Agno Skills **e** recupera um exemplo análogo do corpus de soluções via RAG (`search_knowledge_base`) → propõe `RefactoringProposal`.
- **Critic Agent (Reflection)**: valida sintaxe (ruff/ast) + diff + preservação de lógica/API contra 5 critérios (`ReflectionReview`).

Comunicação **Spec-Driven** via Pydantic em `app/core/schemas.py`.

## Arquitetura

```
app/
├── api/                           # FastAPI: /detect /refactor /knowledge/sync /evaluate/(detector|refactor|critic|all)
├── agents/                        # Detector, Recommender, Critic (db=Postgres p/ RAG/contents)
├── core/                          # config, llm (Mistral|Ollama), prompts, schemas (Pydantic)
├── db/                            # session.py — conexão Postgres (Agno)
├── knowledge/                     # provider.py (RAG via PgVector) + solutions/ (corpus de exemplos)
├── skills/                        # 5 SKILL.md (1 por pattern) — playbook canônico do pattern
├── services/                      # refactor / evaluation / quality_checks
├── tools/                         # ast, heuristic_engine (matriz de smells), diff, syntax
├── utils/                         # retry helper (backoff 429 + retry de schema)
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

O LLM é **plugável** via `LLM_PROVIDER`:

- **`mistral`** (padrão) — API online. Crie uma conta em
  [console.mistral.ai](https://console.mistral.ai), gere uma chave em **API Keys**
  (formato `oj2Z...`) e coloque no `.env` como `LLM_API_KEY=oj2Z...`.
- **`ollama`** — modelos locais (Mistral/Qwen) via Docker. Ver "Modelos locais" abaixo.

> **Conhecimento de patterns (duas camadas):** o Recommender carrega o playbook de cada
> pattern via Agno Skills (`app/skills/*.md`, lookup por nome) **e** recupera exemplos
> análogos por **RAG semântico** (PgVector + embeddings HuggingFace) sobre o corpus
> `app/knowledge/solutions/`. O RAG exige o Postgres no ar e um `HUGGINGFACE_API_KEY`
> (token gratuito), além de uma chamada a `POST /knowledge/sync` para popular o índice.
> Detalhes em [`docs/agentic_patterns.md` §16](docs/agentic_patterns.md).

```bash
cp .env.example .env
# preencha LLM_API_KEY (modo mistral) e HUGGINGFACE_API_KEY (para o RAG)

# instalar deps
uv sync --extra dev
```

Para trocar o modelo (ex.: `mistral-medium-latest`, `mistral-large-latest`), ajuste
`LLM_MODEL_ID` no `.env`.

## Executar

### Local
```bash
uv run python -m uvicorn app.main:app --reload

# se quiser usar o launcher uvicorn direto, recrie a venv para regenerar os binários
# DELETE A PASTA .venv
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

### Docker
```bash
docker compose up -d postgres          # Postgres + pgvector (necessário para o RAG)
curl -X POST http://localhost:8000/api/v1/knowledge/sync   # popula o índice do RAG
docker compose up --build app          # sobe o app
```

### Modelos locais (Ollama) — alternativa à API Mistral
```bash
docker compose up -d ollama            # servidor de modelos locais
docker compose up ollama-pull          # baixa Mistral + Qwen (vários GB)
# então no .env:  LLM_PROVIDER=ollama   LLM_MODEL_ID=mistral  (ou qwen2.5)
```
Permite comparar modelos locais sob a mesma avaliação. Ver [`docs/agentic_patterns.md`](docs/agentic_patterns.md).

## Endpoints

- `POST /api/v1/detect` — apenas o Detector.
- `POST /api/v1/refactor` — pipeline completo Detector → Recommender → Critic com reflection loop.
- `POST /api/v1/knowledge/sync` — indexa o corpus `app/knowledge/solutions/` no pgvector (necessário p/ o RAG).
- `POST /api/v1/evaluate/detector` — **Agente Rastreador**: Falsos Positivos / Falsos Negativos.
- `POST /api/v1/evaluate/refactor` — **Agente Refatorador**: precisão/qualidade da solução.
- `POST /api/v1/evaluate/critic` — **Agente Revisor**: false accept / false reject.
- `POST /api/v1/evaluate/all` — os três relatórios de uma vez.
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
# via CLI — imprime tabelas e gera o relatório (.md auto-contido + .json)
uv run python scripts/run_evaluation.py --all --md dataset/reports/evaluation.md --json dataset/reports/evaluation.json

# via API — relatório completo
curl -X POST http://localhost:8000/api/v1/evaluate/all
```

> Antes de avaliar/usar o Recommender, suba o Postgres e rode `POST /knowledge/sync`
> uma vez para popular o RAG (a tabela nasce vazia). O playbook de cada pattern vive em
> `app/skills/` e é carregado pelo Agno na inicialização — editar uma `SKILL.md` +
> reiniciar o servidor é o ciclo completo para esse conhecimento.

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

# 2. Smoke test ao vivo (precisa de LLM_API_KEY no .env, ou LLM_PROVIDER=ollama)
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

O endpoint agregado `/evaluate/all` também aceita body ad-hoc, com até três seções
opcionais (`detector`, `refactor`, `critic`) — cada uma carrega seu próprio `samples`.
Seções ausentes caem no dataset, então dá pra **misturar** (ex.: rodar o Detector sobre
amostras submetidas e os outros dois sobre o dataset numa única chamada):

```bash
# Misto — só o Detector vai ad-hoc; Refatorador e Revisor seguem com o dataset
curl -X POST http://localhost:8000/api/v1/evaluate/all \
  -H "Content-Type: application/json" \
  -d '{
    "detector": {
      "samples": [
        {"name":"meu_caso","source_code":"class Big: ...","expected_smell":"God Class"}
      ]
    }
  }'
```

#### Exemplo completo — `/evaluate/all` 100% por body

Cada seção precisa de pelo menos uma amostra com seu rótulo esperado. O `payload.json`
abaixo cobre os três agentes simultaneamente sem tocar no `dataset/`:

```bash
cat > /tmp/payload.json <<'JSON'
{
  "detector": {
    "samples": [
      {
        "name": "god_class_caso_1",
        "source_code": "class Big:\n    def m1(self): ...\n    def m2(self): ...\n    def m3(self): ...\n    def m4(self): ...\n    def m5(self): ...\n    def m6(self): ...\n    def m7(self): ...\n    def m8(self): ...\n    def m9(self): ...\n    def m10(self): ...\n    def m11(self): ...\n    def m12(self): ...\n    def m13(self): ...\n    def m14(self): ...\n    def m15(self): ...\n    def m16(self): ...\n    def m17(self): ...\n    def m18(self): ...\n    def m19(self): ...\n    def m20(self): ...\n    def m21(self): ...\n",
        "expected_smell": "God Class"
      },
      {
        "name": "codigo_limpo_1",
        "source_code": "def add(a, b):\n    return a + b\n",
        "expected_smell": "No Smell Detected"
      }
    ]
  },
  "refactor": {
    "samples": [
      {
        "name": "switch_grande",
        "source_code": "def calc(op, a, b):\n    if op == \"sum\":\n        return a + b\n    elif op == \"sub\":\n        return a - b\n    elif op == \"mul\":\n        return a * b\n    elif op == \"div\":\n        return a / b\n    elif op == \"mod\":\n        return a % b\n    else:\n        raise ValueError(op)\n",
        "expected_pattern": "Strategy Pattern"
      },
      {
        "name": "muitos_parametros",
        "source_code": "def criar_usuario(nome, email, senha, idade, cidade, estado, pais):\n    return {\"nome\": nome, \"email\": email, \"senha\": senha, \"idade\": idade, \"cidade\": cidade, \"estado\": estado, \"pais\": pais}\n",
        "expected_pattern": "Builder/Parameter Object"
      }
    ]
  },
  "critic": {
    "samples": [
      {
        "name": "solucao_correta_strategy",
        "problem_code": "def calc(op, a, b):\n    if op == \"sum\": return a+b\n    elif op == \"sub\": return a-b\n",
        "solution_code": "class Operacao:\n    def executar(self, a, b): ...\nclass Soma(Operacao):\n    def executar(self, a, b): return a + b\nclass Sub(Operacao):\n    def executar(self, a, b): return a - b\ndef calc(op: Operacao, a, b):\n    return op.executar(a, b)\n",
        "applied_pattern": "Strategy Pattern",
        "expected_approved": true
      },
      {
        "name": "solucao_incorreta_pattern_errado",
        "problem_code": "def calc(op, a, b):\n    if op == \"sum\": return a+b\n    elif op == \"sub\": return a-b\n",
        "solution_code": "def calc(op, a, b, c=None, d=None):\n    if op == \"sum\": return a+b\n    elif op == \"sub\": return a-b\n",
        "applied_pattern": "Builder/Parameter Object",
        "expected_approved": false,
        "defect_kind": "wrong_pattern"
      }
    ]
  }
}
JSON

curl -X POST http://localhost:8000/api/v1/evaluate/all \
  -H "Content-Type: application/json" \
  -d @/tmp/payload.json | python -m json.tool
```

A resposta tem o mesmo formato do modo dataset — `FullEvaluationReport` com as três
seções (`detector`, `refactor`, `critic`), cada uma com matriz de confusão, métricas e
`per_file` listando cada amostra enviada:

```json
{
  "detector": { "total": 2, "precision": 1.0, "recall": 1.0, "per_file": [ {"file": "god_class_caso_1", ... } ] },
  "refactor": { "total": 2, "accuracy": 0.5, "pattern_accuracy": 1.0, "per_file": [ {"file": "switch_grande", ... } ] },
  "critic":   { "total": 2, "accuracy": 1.0, "false_accept_rate": 0.0, "per_file": [ {"solution_file": "solucao_correta_strategy", ... } ] }
}
```

## Tests

```bash
uv run pytest
```

Cobertura: tools determinísticas (AST, matriz heurística, diff, syntax) + métricas de
avaliação + integridade do dataset. Os agentes em si são testados via dataset de avaliação
(não via mocks, conforme metodologia acadêmica).
