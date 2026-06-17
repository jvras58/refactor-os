# Como Usar a Aplicação

Guia prático para subir o `refactor-os` e exercitar a pipeline.

## 1. Pré-requisitos

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) para dependências
- Docker (opcional, só para empacotar o app)
- Chave da Mistral (`MISTRAL_API_KEY`) — gratuita em [console.mistral.ai](https://console.mistral.ai) → **API Keys** → *Create API Key* (formato `oj2Z...`)

> O conhecimento dos patterns vive em `app/skills/<pattern>/SKILL.md` e é
> carregado sob demanda pelo Recommender via Agno Skills. O Detector é
> **stateless por chamada** (sem `db=`); o Recommender usa Postgres+pgvector
> só para o RAG do corpus de soluções.
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
| POST   | `/detect`          | Executa **somente** o Detector multi-label — retorna `DetectionScanResult` (8 vereditos + heurística). Código inválido → `422`. |
| POST   | `/refactor`        | Pipeline completa (Detector→Recommender→Critic + reflection). |
| POST   | `/evaluate/detector` | Avalia o Detector (multi-label, FP/FN por tipo). Body vazio → dataset; body com `samples` → código submetido. |
| POST   | `/evaluate/refactor` | Avalia o Recommender (qualidade/refatoração). Body vazio → dataset; body com `samples` → código submetido. |
| POST   | `/evaluate/critic`  | Avalia o Critic (false accept/false reject). **Exige `samples`** — o dataset atual não traz soluções rotuladas. |
| POST   | `/evaluate/all`     | Roda as 3 avaliações de uma vez. Detector/Refatorador sem seção caem no dataset; o Critic precisa da seção `critic` com `samples`. |

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

Resposta (`DetectionScanResult`, resumida — são 8 `type_results`, um por tipo):

```json
{
  "heuristic_scan": {
    "signals": {
      "Long Parameter List": {"possible": true, "score": 0.6, "line_start": 1, "line_end": 1, "evidence": ["Função `f` com 6 parâmetros (limite 5)."]},
      "God Class": {"possible": false, "score": 0.0}
    }
  },
  "type_results": [
    {"type_name": "Long Parameter List", "detected": true,
     "evidencias": [{"local": "f", "linhas": [1, 1]}],
     "reasoning": "Função com 6 parâmetros..."},
    {"type_name": "God Class", "detected": false, "evidencias": [], "reasoning": "..."}
  ]
}
```

> Cada chamada ao `/detect` custa **8 chamadas de LLM** (uma por smell/pattern).

### Passo 2 — Pipeline completa

```python
import requests, pathlib

src = pathlib.Path("dataset/examples/code_smell/long-parameter-list/example_1.py").read_text()
r = requests.post(
    "http://127.0.0.1:8000/api/v1/refactor",
    json={"source_code": src, "file_name": "example_1.py"},
)
result = r.json()
print(result["approved"], result["iterations"])
print(result["detected_problems"], result["target_pattern"])
print(result["proposal"]["refactored_code"])
```

Resposta (`RefactorResult`):
- `detection` — `DetectionScanResult` (scan multi-label completo).
- `detected_problems` — lista dos smells/patterns detectados.
- `target_smell` / `target_pattern` — o alvo escolhido para a refatoração.
- `proposal` — `RefactoringProposal` (código refatorado + explicação).
- `review` — `ReflectionReview` (aprovado ou crítica final).
- `iterations` — quantas iterações de reflection rodaram.
- `approved` — `True` se o Critic aprovou.

### Passo 3 — Avaliação empírica

Detector e Refatorador: sem body → dataset fixo; com `samples` → código submetido.
Critic: sempre com `samples` (rótulo esperado obrigatório).

```bash
# Detector + Refatorador sobre o dataset (Critic é pulado sem samples)
uv run python scripts/run_evaluation.py --detector --refactor

# Avaliação do Detector sobre código submetido (multi-label)
curl -X POST http://127.0.0.1:8000/api/v1/evaluate/detector \
  -H "Content-Type: application/json" \
  -d '{"samples":[{"name":"meu_teste","source_code":"def add(a,b): return a+b\n","expected_problems":[]}]}'
```

Resposta do Detector (`DetectorMetrics`):

```json
{
  "total_files": 30,
  "confusion": {"true_positive": 52, "false_negative": 6, "false_positive": 9, "true_negative": 173},
  "precision": 0.85, "recall": 0.90, "f1": 0.87,
  "exact_match_rate": 0.63,
  "per_file": [
    {"file": "mixed/example_1.py", "expected_problems": ["God Class", "Facade"],
     "detected_problems": ["God Class"], "missing": ["Facade"], "extra": [], "exact_match": false}
  ]
}
```

Veja `Readme.md` → *Avaliação com código submetido (ad-hoc)* para o schema completo
das amostras por agente.

## 6. Uso programático (sem HTTP)

```python
import asyncio

from app.core.schemas import RefactorRequest
from app.services.refactor_service import RefactorService

service = RefactorService()
result = asyncio.run(service.run(RefactorRequest(source_code=open("script.py").read())))
print(result.approved, result.detected_problems, result.target_pattern)
```

Só a detecção multi-label (sem Recommender/Critic — não precisa de Postgres):

```python
import asyncio

from app.services.detector_service import MultiDetectorService

service = MultiDetectorService()
scan = asyncio.run(service.detect(open("script.py").read()))
print(service.compile(scan))   # ex.: ["God Class", "Facade"]
```

## 7. Expandindo o dataset (ground truth)

1. Adicione o exemplo em `dataset/examples/<categoria>/example_N.py`.
2. Acrescente uma entrada em `dataset/ground_truth_detector.json` — o caminho é
   relativo a `dataset/examples/` e `problems` lista **todos** os smells/patterns
   presentes (lista vazia = código limpo):
   ```json
   {
     "file": "code_smell/god-class/example_4.py",
     "problems": ["God Class", "Facade"]
   }
   ```
3. Rode `uv run python scripts/run_evaluation.py --detector` (ou
   `POST /api/v1/evaluate/detector`) novamente.

## 8. Testes

```bash
uv run pytest
```

Cobre as tools determinísticas (`heuristic_engine`, `diff`, `syntax`, `logic_signals`),
as fases determinísticas do multi-detector e as métricas de avaliação.
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
| `422` no `/detect`                          | Código enviado não compila como Python.    | Corrija a sintaxe — a fase 1 do detector valida com `ast.parse`. |
| `/detect` demorado                          | São 8 chamadas de LLM por requisição (com throttle anti-429). | Esperado; use `scripts/run_multi_detector.py` (checkpoint resumível) para lotes. |
| Reflection sempre estoura `iterations=3`   | Crítica do Critic não está sendo acionável. | Ajuste o prompt em `app/core/prompts.py`.            |
