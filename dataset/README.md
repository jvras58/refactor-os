# Dataset — Ground Truth para Avaliação Empírica

Este dataset alimenta as **três avaliações independentes** do pipeline (uma por agente),
seguindo o escopo pedido na disciplina: **10 problemas + 10 soluções** por eixo.

## Estrutura

```
dataset/
├── examples/            # 10 programas COM bad smell (2 por categoria)
├── clean/               # 10 programas LIMPOS (sem smell — testam Falsos Positivos)
├── solutions/
│   ├── correct/         # 10 refatorações CORRETAS (o Revisor deve aprovar)
│   └── incorrect/       # 10 refatorações INCORRETAS (o Revisor deve reprovar)
├── ground_truth.json    # gabarito do Detector: 20 entradas (10 smell + 10 limpas)
└── critic_truth.json    # gabarito do Critic: 20 soluções rotuladas (10 ok + 10 com defeito)
```

Os caminhos em `ground_truth.json` / `critic_truth.json` são **relativos a `dataset/`**
(ex.: `examples/01_complex_switch.py`).

## As três métricas

### 1. Agente Rastreador (Detector) — `POST /api/v1/evaluate/detector`
Matriz de confusão sobre `examples/` (positivos) + `clean/` (negativos):
- **Falsos Negativos** — código tem smell mas o agente disse que não (deixou passar).
- **Falsos Positivos** — código está limpo mas o agente apontou smell (viu onde não há).
- Reporta Precision, Recall, Accuracy, Specificity, F1 e acerto do *tipo* de smell.

### 2. Agente Refatorador (Recommender) — `POST /api/v1/evaluate/refactor`
Para cada um dos 10 problemas, roda o pipeline e checa a solução por três eixos objetivos:
- **pattern correto** (bate com o esperado para o smell);
- **sintaxe válida** (`ast` + ruff);
- **API pública preservada** (nenhuma função/classe/método público desaparece).

Uma solução é "correta" quando satisfaz os três. `solutions/correct/` é a referência ideal.

### 3. Agente Revisor (Critic) — `POST /api/v1/evaluate/critic`
Alimenta o Critic isoladamente com as 20 soluções rotuladas e mede a confiabilidade:
- **False Accept** — aprovou uma solução incorreta (disse que estava correta);
- **False Reject** — reprovou uma solução correta (disse que estava incorreta).

Cada solução incorreta declara um `defect_kind` (`syntax`, `logic`, `signature`,
`pattern_not_applied`, `forbidden_import`).

## Como rodar

```bash
docker compose up -d postgres
curl -X POST http://localhost:8000/api/v1/knowledge/sync   # indexa os patterns
# via CLI — gera dataset/reports/evaluation.{md,json} (o .md é auto-contido por seção):
uv run python scripts/run_evaluation.py --all --md dataset/reports/evaluation.md --json dataset/reports/evaluation.json
# ou via API:
curl -X POST http://localhost:8000/api/v1/evaluate/all
```

## Como expandir
1. Adicione `NN_descricao.py` em `examples/` (smell) ou `clean/` (limpo) e a entrada
   correspondente em `ground_truth.json`.
2. Para o Critic, adicione a refatoração em `solutions/correct|incorrect/` e uma entrada
   em `critic_truth.json` (com `defect_kind` quando `expected_approved=false`).
3. Mantenha o par 10/10 balanceado para métricas comparáveis.
