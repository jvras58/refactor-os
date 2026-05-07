# Como Usar a Aplicação

Guia prático para subir o `refactor-os` e exercitar a pipeline.

## 1. Pré-requisitos

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) para dependências
- Docker (opcional, para Postgres+pgvector)
- Chave da Groq (`GROQ_API_KEY`) — gratuita em [console.groq.com](https://console.groq.com) → **API Keys** → *Create API Key* (formato `gsk_...`)
- Token do HuggingFace (`HUGGINGFACE_API_KEY`) — gratuito em [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → *New token* → tipo **Read** (formato `hf_...`). Usado para embeddings via Inference API, sem custo.

## 2. Setup

```bash
git clone <repo>
cd refactor-os
cp .env.example .env       # preencha GROQ_API_KEY
uv sync --extra dev
```

`.env` mínimo:

```env
GROQ_API_KEY=gsk_...
LLM_MODEL_ID=llama-3.3-70b-versatile
HUGGINGFACE_API_KEY=hf_...
DB_URL=postgresql+psycopg://ai:ai@localhost:5532/ai
MAX_REFLECTION_ITERATIONS=3
```

> Outros modelos Llama disponíveis na Groq: `llama-3.1-8b-instant` (mais rápido / barato),
> `meta-llama/llama-4-scout-17b-16e-instruct`. Basta trocar `LLM_MODEL_ID`.

## 3. Subir o Postgres (PgVector)

```bash
docker compose up -d postgres
```

Sobe `agnohq/pgvector:16` na porta `5532`. Healthcheck embutido.

> **Embeddings via HuggingFace Inference API (gratuita):** o projeto usa
> `HuggingfaceCustomEmbedder` com `BAAI/bge-small-en-v1.5` (384 dims) — sem custo, sem
> compilação Rust. Requer apenas `HUGGINGFACE_API_KEY` (token Read gratuito do HF).
>
> Se você migrou de uma instalação que indexou com embeddings de 1536 dimensões (default
> OpenAI), dropar a tabela do KB antes de re-indexar:
> ```bash
> docker compose exec postgres psql -U ai -d ai -c "DROP TABLE IF EXISTS ai.design_patterns_kb;"
> ```

## 4. Rodar a aplicação

### Desenvolvimento (reload automático)

```bash
uv run uvicorn app.main:app --reload
```

API em `http://127.0.0.1:8000`. Docs Swagger em `/docs`.

### Stack completa via Docker

```bash
docker compose up --build
```

## 5. Endpoints

Base: `http://127.0.0.1:8000/api/v1`

| Método | Rota               | O que faz                                                   |
|--------|--------------------|-------------------------------------------------------------|
| GET    | `/health`          | Liveness check.                                             |
| POST   | `/detect`          | Executa **somente** o Detector — retorna `SmellDetection`.  |
| POST   | `/refactor`        | Pipeline completa (Detector→Recommender→Critic + reflection). |
| POST   | `/evaluate`        | Roda o `dataset/` e retorna métricas (precision/recall/accuracy). |
| POST   | `/knowledge/sync`  | Indexa os 5 `.md` de patterns no PgVector.                  |

## 6. Fluxo recomendado de uso

### Passo 1 — Indexar a base de patterns (uma vez)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/sync
# → {"loaded": 5}
```

### Passo 2 — Testar a detecção isolada

```bash
curl -X POST http://127.0.0.1:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "def f(a,b,c,d,e,f): return a+b+c+d+e+f"
  }'
```

Resposta (resumida):

```json
{
  "has_smell": true,
  "smell_type": "Long Parameter List",
  "line_start": 1,
  "line_end": 1,
  "affected_snippet": "def f(a,b,c,d,e,f): return a+b+c+d+e+f",
  "reasoning": "Função com 6 parâmetros (>=5)..."
}
```

### Passo 3 — Pipeline completa

```bash
curl -X POST http://127.0.0.1:8000/api/v1/refactor \
  -H "Content-Type: application/json" \
  -d @dataset/examples/02_long_parameter_list.py.json
```

Ou em Python:

```python
import requests, pathlib

src = pathlib.Path("dataset/examples/02_long_parameter_list.py").read_text()
r = requests.post(
    "http://127.0.0.1:8000/api/v1/refactor",
    json={"source_code": src, "file_name": "02_long_parameter_list.py"},
)
result = r.json()
print(result["approved"], result["iterations"])
print(result["proposal"]["refactored_code"])
```

Resposta (`RefactorResult`):
- `detection` — `SmellDetection`.
- `proposal` — `RefactoringProposal` (código refatorado + explicação).
- `review` — `ReflectionReview` (aprovado ou crítica final).
- `iterations` — quantas iterações de reflection rodaram.
- `approved` — `True` se o Critic aprovou.

### Passo 4 — Avaliação empírica

```bash
curl -X POST http://127.0.0.1:8000/api/v1/evaluate
```

Resposta:

```json
{
  "total": 5,
  "detector_precision": 1.0,
  "detector_recall": 1.0,
  "refactor_accuracy": 0.8,
  "per_file": [ ... ]
}
```

## 7. Uso programático (sem HTTP)

```python
from app.core.schemas import RefactorRequest
from app.services.refactor_service import RefactorService

service = RefactorService()
result = service.run(RefactorRequest(source_code=open("script.py").read()))
print(result.approved, result.proposal.applied_pattern)
```

## 8. Expandindo o dataset (ground truth)

1. Adicione `dataset/examples/NN_descricao.py` com o smell intencional.
2. Acrescente uma entrada em `dataset/ground_truth.json`:
   ```json
   {
     "file": "06_outro_smell.py",
     "smell_type": "God Class",
     "expected_pattern": "Facade/SRP",
     "line_start": 10,
     "line_end": 80
   }
   ```
3. Rode `POST /api/v1/evaluate` novamente.

Veja `dataset/README.md` para detalhes da metodologia.

## 9. Testes

```bash
uv run pytest
```

Cobre as tools determinísticas (`ast`, `diff`, `pattern_registry`, `syntax`).
Os agentes em si são exercitados pelo dataset de avaliação.

## 10. Variáveis de ambiente úteis

| Var                          | Default                                              | Descrição                         |
|------------------------------|------------------------------------------------------|-----------------------------------|
| `GROQ_API_KEY`               | —                                                    | Obrigatória (gere em console.groq.com). |
| `LLM_MODEL_ID`               | `llama-3.3-70b-versatile`                            | Modelo Llama servido pela Groq.   |
| `DB_URL`                     | `postgresql+psycopg://ai:ai@localhost:5532/ai`       | Postgres+pgvector.                |
| `KNOWLEDGE_TABLE`            | `design_patterns_kb`                                 | Tabela do KB.                     |
| `MAX_REFLECTION_ITERATIONS`  | `3`                                                  | Limite do reflection loop.        |
| `LOG_LEVEL`                  | `INFO`                                               | Nível de log.                     |
| `API_HOST` / `API_PORT`      | `0.0.0.0` / `8000`                                   | Host e porta do uvicorn.          |

## 11. Troubleshooting

| Sintoma                                    | Causa provável                              | Ação                                                 |
|--------------------------------------------|---------------------------------------------|------------------------------------------------------|
| `GROQ_API_KEY is required`                 | `.env` não preenchido.                      | Preencha `GROQ_API_KEY` (gere em console.groq.com).  |
| `401 Unauthorized` da Groq                 | Chave inválida / revogada.                  | Gere uma nova em console.groq.com → API Keys.        |
| Conexão recusada na porta 5532             | Postgres não subiu.                         | `docker compose up -d postgres`.                     |
| `output_schema` não respeitado pelo modelo | Modelo Llama pequeno demais.                | Use `llama-3.3-70b-versatile` ou superior.           |
| Reflection sempre estoura `iterations=3`   | Crítica do Critic não está sendo acionável. | Ajuste o prompt em `app/core/prompts.py`.            |
