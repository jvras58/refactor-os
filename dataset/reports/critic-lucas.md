# Relatório de Avaliação — refactor-os

_Gerado em 2026-06-22 19:53_

Avaliação independente dos três agentes do pipeline (Rastreador → Refatorador → Revisor).

## 3. Agente Revisor (Critic)

**False Accept (aprovou incorreta):** 0 (FAR=0.000)  •  **False Reject (reprovou correta):** 0 (FRR=0.000)

| Métrica | Valor |
|---|---|
| Accuracy | 1.000 |
| Precision | 1.000 |
| Recall | 1.000 |
| F1 | 1.000 |

### Matriz de confusão

| | Critic aprovou | Critic reprovou |
|---|:---:|:---:|
| **Solução correta** | 10 (TP) | 0 (FN) |
| **Solução incorreta** | 0 (FP) | 10 (TN) |

### Detalhe por solução

| Solução | Classe | Defeito |
|---|:---:|---|
| solutions/correct/sol_01_complex_switch.py | TP | - |
| solutions/correct/sol_02_long_parameter_list.py | TP | - |
| solutions/correct/sol_03_god_class.py | TP | - |
| solutions/correct/sol_04_tight_coupling.py | TP | - |
| solutions/correct/sol_05_duplicated_code.py | TP | - |
| solutions/correct/sol_06_complex_switch.py | TP | - |
| solutions/correct/sol_07_long_parameter_list.py | TP | - |
| solutions/correct/sol_08_god_class.py | TP | - |
| solutions/correct/sol_09_tight_coupling.py | TP | - |
| solutions/correct/sol_10_duplicated_code.py | TP | - |
| solutions/incorrect/bad_01_complex_switch.py | TN | logic |
| solutions/incorrect/bad_02_long_parameter_list.py | TN | syntax |
| solutions/incorrect/bad_03_god_class.py | TN | signature |
| solutions/incorrect/bad_04_tight_coupling.py | TN | pattern_not_applied |
| solutions/incorrect/bad_05_duplicated_code.py | TN | logic |
| solutions/incorrect/bad_06_complex_switch.py | TN | syntax |
| solutions/incorrect/bad_07_long_parameter_list.py | TN | forbidden_import |
| solutions/incorrect/bad_08_god_class.py | TN | logic |
| solutions/incorrect/bad_09_tight_coupling.py | TN | logic |
| solutions/incorrect/bad_10_duplicated_code.py | TN | pattern_not_applied |
