# Relatório de Avaliação — refactor-os

_Gerado em 2026-06-22 18:52_

Avaliação independente dos três agentes do pipeline (Rastreador → Refatorador → Revisor).

## 2. Agente Refatorador (Recommender)

**Accuracy (totalmente correto):** 0.800 sobre 10 problemas

| Métrica | Valor |
|---|---|
| Pattern correto | 1.000 |
| Sintaxe válida | 1.000 |
| API pública preservada | 0.800 |
| Aprovado pelo Critic | 0.800 |
| Iterações médias | 1.70 |

### Detalhe por problema

| Arquivo | Pattern | Sintaxe | API | OK | Esperado → Aplicado |
|---|:---:|:---:|:---:|:---:|---|
| examples/01_complex_switch.py | ✓ | ✓ | ✓ | ✓ | Strategy Pattern → Strategy Pattern |
| examples/02_long_parameter_list.py | ✓ | ✓ | ✓ | ✓ | Builder/Parameter Object → Builder/Parameter Object |
| examples/03_god_class.py | ✓ | ✓ | ✓ | ✓ | Facade/SRP → Facade/SRP |
| examples/04_tight_coupling.py | ✓ | ✓ | ✓ | ✓ | Dependency Injection → Dependency Injection |
| examples/05_duplicated_code.py | ✓ | ✓ | ✗ | ✗ | Template Method → Template Method |
| examples/06_complex_switch.py | ✓ | ✓ | ✓ | ✓ | Strategy Pattern → Strategy Pattern |
| examples/07_long_parameter_list.py | ✓ | ✓ | ✓ | ✓ | Builder/Parameter Object → Builder/Parameter Object |
| examples/08_god_class.py | ✓ | ✓ | ✓ | ✓ | Facade/SRP → Facade/SRP |
| examples/09_tight_coupling.py | ✓ | ✓ | ✓ | ✓ | Dependency Injection → Dependency Injection |
| examples/10_duplicated_code.py | ✓ | ✓ | ✗ | ✗ | Template Method → Template Method |
