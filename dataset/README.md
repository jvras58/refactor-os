# Dataset — Ground Truth para Avaliação Empírica

Cada arquivo em `examples/` contém **intencionalmente** uma instância de um dos 5 bad smells
do escopo. O arquivo `ground_truth.json` registra a localização canônica do smell e o
Design Pattern esperado pela refatoração ideal.

## Métricas de avaliação
O `EvaluationService` consome este dataset e produz:
- **Detector Precision/Recall** — taxa de acerto na identificação do smell.
- **Refactor Accuracy** — taxa em que o pattern aprovado coincide com o esperado.

## Como expandir até 20 scripts
1. Adicione um arquivo `NN_descricao.py` em `examples/`.
2. Acrescente uma entrada em `ground_truth.json` com:
   - `file`: nome do arquivo.
   - `smell_type`: um dos enums em `BadSmellType`.
   - `expected_pattern`: um dos enums em `DesignPatternType`.
   - `line_start` / `line_end`: localização do smell no original.

## Estado atual
20 exemplos curados (4 por categoria de smell) para avaliacao isolada do Recommender Agent.
