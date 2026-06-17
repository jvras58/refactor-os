# Dataset — Ground Truth Multi-Label do Detector

Este dataset alimenta a avaliação **multi-label** do Detector (e, por derivação, a do
Refatorador): cada exemplo é rotulado com **todos** os smells e patterns presentes —
um arquivo pode ter vários problemas ao mesmo tempo, ou nenhum.

## Estrutura

```
dataset/
├── examples/
│   ├── code_smell/
│   │   ├── complex-switch-statements/   # 3 exemplos do smell
│   │   ├── long-parameter-list/         # 3 exemplos
│   │   ├── god-class/                   # 3 exemplos
│   │   └── duplicated-code/             # 3 exemplos
│   ├── patterns/
│   │   ├── strategy-pattern/            # 3 exemplos onde o pattern é aplicável
│   │   ├── builder/                     # 3 exemplos
│   │   ├── facade/                      # 3 exemplos
│   │   └── template-method/             # 3 exemplos
│   ├── mixed/                           # 3 exemplos com MÚLTIPLOS problemas simultâneos
│   └── complex-clean/                   # 3 exemplos complexos porém limpos (medem Falsos Positivos)
└── ground_truth_detector.json           # gabarito: lista `problems` por arquivo
```

Os caminhos em `ground_truth_detector.json` são **relativos a `dataset/examples/`**
(ex.: `code_smell/god-class/example_1.py`).

## Formato do gabarito

Cada entrada mapeia um arquivo para a lista de problemas presentes. Lista vazia =
código limpo:

```json
{
  "file": "mixed/example_1.py",
  "problems": ["God Class", "Facade", "Long Parameter List",
               "Complex/Long Switch Statements", "Strategy Pattern"]
}
```

Valores aceitos em `problems` (schema `GroundTruthEntry` em `app/core/schemas.py`):

| Smells (`SmellType`) | Patterns (`PatternType`) |
|---|---|
| `Complex/Long Switch Statements` | `Strategy Pattern` |
| `Long Parameter List` | `Builder` |
| `God Class` | `Facade` |
| `Duplicated Code` | `Template Method` |

Importante: **smell e pattern são rótulos independentes** — um pattern pode ser
aplicável sem o smell irmão estar presente (ex.: `patterns/builder/example_1.py` pede
Builder sem ter Long Parameter List), e vice-versa. É exatamente isso que a detecção
multi-label mede.

## Como o dataset é usado

### 1. Agente Rastreador (Detector) — `POST /api/v1/evaluate/detector`
Para cada arquivo, o detector produz 8 decisões binárias (4 smells + 4 patterns),
comparadas com `problems`:
- **Falso Negativo** — o tipo estava presente mas o detector não o marcou (deixou passar);
- **Falso Positivo** — o detector marcou um tipo ausente (viu onde não há).
- Reporta Precision, Recall, Accuracy, Specificity, F1 e **exact match** (fração de
  arquivos cujo conjunto detectado bate exatamente com o esperado).

### 2. Agente Refatorador (Recommender) — `POST /api/v1/evaluate/refactor`
Para cada entrada com `problems` não-vazio, roda o pipeline completo. O pattern
esperado é derivado da própria lista (pattern explícito, ou o mapeado do primeiro
smell) e a solução é checada por eixos objetivos: pattern correto, sintaxe válida
(`ast` + ruff) e lógica/API pública preservadas.

### 3. Agente Revisor (Critic) — `POST /api/v1/evaluate/critic`
Este dataset **não traz soluções rotuladas** para o Critic — a avaliação dele roda
apenas em modo ad-hoc, com `samples` no body (par problema/solução + veredito
esperado). Ver `Readme.md` → *Avaliação com código submetido*.

## Como rodar

```bash
# detector em lote com checkpoint resumível (cada arquivo custa 8 chamadas de LLM)
uv run python scripts/run_multi_detector.py --limit 2    # teste com 2 arquivos antes
uv run python scripts/run_multi_detector.py              # dataset inteiro (retoma de onde parou)

# métricas do Detector + Refatorador (gera dataset/reports/evaluation.{md,json})
uv run python scripts/run_evaluation.py --detector --refactor \
  --md dataset/reports/evaluation.md --json dataset/reports/evaluation.json

# ou via API:
curl -X POST http://localhost:8000/api/v1/evaluate/detector
```

## Como expandir

1. Adicione o exemplo em `examples/<categoria>/example_N.py`.
2. Acrescente a entrada em `ground_truth_detector.json` com **todos** os problemas
   presentes (lista vazia se for um exemplo limpo).
3. Rode `uv run pytest tests/test_dataset_integrity.py` — valida que todo arquivo do
   gabarito existe, compila e usa apenas tipos do escopo.
