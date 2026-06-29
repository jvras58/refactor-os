# Como Usar a Aplicação

Guia prático para subir o `refactor-os` e exercitar a pipeline.

## 1. Pré-requisitos

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) para dependências
- Docker (opcional, só para empacotar o app)
- Chave da Mistral (`MISTRAL_API_KEY`) — gratuita em [console.mistral.ai](https://console.mistral.ai) → **API Keys** → *Create API Key* (formato `oj2Z...`)

> **Sem embeddings, sem HuggingFace, sem Postgres.** O conhecimento dos 5
> patterns vive em `app/skills/<pattern>/SKILL.md` e é carregado sob demanda
> pelo Recommender via Agno Skills. Os agentes são **stateless por chamada**
> (Agno aceita `db=None`), então não precisam de sessão persistida.
> Justificativa em [`agentic_patterns.md` §16](agentic_patterns.md#16--skills-substituem-rag-decisão-arquitetural).

## 2. Setup

```bash
git clone <repo>
cd refactor-os
cp .env.example .env       # preencha MISTRAL_API_KEY
uv sync --extra dev
```

`.env` mínimo:

```env
MISTRAL_API_KEY=oj2ZA...
LLM_MODEL_ID=mistral-medium-latest
MAX_REFLECTION_ITERATIONS=3
```

## 3. Rodar a aplicação

### Desenvolvimento (reload automático)

```bash
uv run uvicorn app.main:app --reload
```

API em `http://127.0.0.1:8000`. Docs Swagger em `/docs`.

### Via Docker

```bash
docker compose up --build
```

## 4. Endpoints

Base: `http://127.0.0.1:8000/api/v1`

| Método | Rota               | O que faz                                                   |
|--------|--------------------|-------------------------------------------------------------|
| GET    | `/health`          | Liveness check.                                             |
| POST   | `/detect`          | Executa **somente** o Detector — retorna `SmellDetection`.  |
| POST   | `/refactor`        | Pipeline completa (Detector→Recommender→Critic + reflection). |
| POST   | `/evaluate/detector` | Avalia o Detector (FP/FN). Body vazio → dataset; body com `samples` → código submetido. |
| POST   | `/evaluate/refactor` | Avalia o Recommender (qualidade/refatoração). Body vazio → dataset; body com `samples` → código submetido. |
| POST   | `/evaluate/critic`  | Avalia o Critic (false accept/false reject). Body vazio → dataset; body com `samples` → código submetido. |
| POST   | `/evaluate/all`     | Roda as 3 avaliações de uma vez. Body vazio → tudo no dataset; body com `detector`/`refactor`/`critic` → cada seção pode ir ad-hoc independentemente. |

> `POST /api/v1/knowledge/sync` indexa o corpus `app/knowledge/solutions/` no
> pgvector (upsert idempotente). A tabela nasce **vazia** — chame esse endpoint
> uma vez após subir o Postgres (`docker compose up -d postgres`) e definir
> `HUGGINGFACE_API_KEY`. A estrutura canônica dos patterns vive nos skills em
> `app/skills/`, carregados à parte na inicialização do Recommender (Agno faz sozinho).

## 5. Fluxo recomendado de uso

### Passo 1 — Testar a detecção isolada

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

### Passo 2 — Pipeline completa

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

### Passo 3 — Avaliação empírica

Cada agente é avaliado de forma independente. Sem body → roda sobre o dataset fixo;
com `samples` no body → roda sobre o código submetido (rótulo esperado obrigatório).

```bash
# Relatório completo dos três agentes sobre o dataset
curl -X POST http://127.0.0.1:8000/api/v1/evaluate/all

# Avaliação do Detector sobre código submetido
curl -X POST http://127.0.0.1:8000/api/v1/evaluate/detector \
  -H "Content-Type: application/json" \
  -d '{"samples":[{"name":"meu_teste","source_code":"def add(a,b): return a+b\n","expected_smell":"No Smell Detected"}]}'
```

Resposta agregada (`/evaluate/all`):

```json
{
  "detector": { "total": 20, "precision": 1.0, "recall": 1.0, "per_file": [ ... ] },
  "refactor": { "total": 10, "accuracy": 0.8, "pattern_accuracy": 0.9, "per_file": [ ... ] },
  "critic":   { "total": 20, "accuracy": 0.9, "false_accept_rate": 0.1, "per_file": [ ... ] }
}
```

Veja `Readme.md` → *Avaliação com código submetido (ad-hoc)* para o schema completo
das amostras por agente.

## 6. Uso programático (sem HTTP)

```python
from app.core.schemas import RefactorRequest
from app.services.refactor_service import RefactorService

service = RefactorService()
result = service.run(RefactorRequest(source_code=open("script.py").read()))
print(result.approved, result.proposal.applied_pattern)
```

## 7. Expandindo o dataset (ground truth)

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
3. Rode `POST /api/v1/evaluate/all` novamente.

Veja `dataset/README.md` para detalhes da metodologia.

## 8. Testes

```bash
uv run pytest
```

Cobre as tools determinísticas (`ast`, `diff`, `syntax`).
Os agentes em si são exercitados pelo dataset de avaliação.

## 9. Variáveis de ambiente úteis

| Var                          | Default                                              | Descrição                         |
|------------------------------|------------------------------------------------------|-----------------------------------|
| `MISTRAL_API_KEY`            | —                                                    | Obrigatória (gere em https://console.mistral.ai). |
| `LLM_MODEL_ID`               | `mistral-medium-latest`                              | Modelo Mistral servido pela Mistral.   |
| `MAX_REFLECTION_ITERATIONS`  | `3`                                                  | Limite do reflection loop.        |
| `LOG_LEVEL`                  | `INFO`                                               | Nível de log.                     |
| `API_HOST` / `API_PORT`      | `0.0.0.0` / `8000`                                   | Host e porta do uvicorn.          |

## 10. Troubleshooting

| Sintoma                                    | Causa provável                              | Ação                                                 |
|--------------------------------------------|---------------------------------------------|------------------------------------------------------|
| `MISTRAL_API_KEY is required`                 | `.env` não preenchido.                      | Preencha `MISTRAL_API_KEY` (gere em https://console.mistral.ai).  |
| `401 Unauthorized` da Mistral                 | Chave inválida / revogada.                  | Gere uma nova em https://console.mistral.ai → API Keys.        |
| Reflection sempre estoura `iterations=3`   | Crítica do Critic não está sendo acionável. | Ajuste o prompt em `app/core/prompts.py`.            |
