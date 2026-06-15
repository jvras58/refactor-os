# Relatório de Avaliação — refactor-os

_Gerado em 2026-06-29 18:57_

Avaliação independente dos três agentes do pipeline (Rastreador → Refatorador → Revisor).

## 1. Agente Rastreador (Detector)

**Falsos Negativos (deixou passar):** 0  •  **Falsos Positivos (viu onde não há):** 0

| Métrica | Valor |
|---|---|
| Precision | 1.000 |
| Recall | 1.000 |
| Accuracy | 1.000 |
| Specificity | 1.000 |
| F1 | 1.000 |
| FPR (taxa de falso positivo) | 0.000 |
| FNR (taxa de falso negativo) | 0.000 |
| Acerto do tipo de smell | 1.000 |

### Matriz de confusão

| | Detectou smell | Disse limpo |
|---|:---:|:---:|
| **Esperado: tem smell** | 10 (TP) | 0 (FN) |
| **Esperado: limpo** | 0 (FP) | 10 (TN) |

### Detalhe por arquivo

| Arquivo | Classe | Esperado | Detectado |
|---|:---:|---|---|
| examples/01_complex_switch.py | TP | Complex/Long Switch Statements | Complex/Long Switch Statements |
| examples/02_long_parameter_list.py | TP | Long Parameter List | Long Parameter List |
| examples/03_god_class.py | TP | God Class | God Class |
| examples/04_tight_coupling.py | TP | Tight Coupling | Tight Coupling |
| examples/05_duplicated_code.py | TP | Duplicated Code | Duplicated Code |
| examples/06_complex_switch.py | TP | Complex/Long Switch Statements | Complex/Long Switch Statements |
| examples/07_long_parameter_list.py | TP | Long Parameter List | Long Parameter List |
| examples/08_god_class.py | TP | God Class | God Class |
| examples/09_tight_coupling.py | TP | Tight Coupling | Tight Coupling |
| examples/10_duplicated_code.py | TP | Duplicated Code | Duplicated Code |
| clean/clean_01_dict_dispatch.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_02_parameter_object.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_03_focused_class.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_04_injected_dependency.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_05_template_method.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_06_pure_functions.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_07_short_switch.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_08_validator.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_09_value_object.py | TN | No Smell Detected | No Smell Detected |
| clean/clean_10_repository_protocol.py | TN | No Smell Detected | No Smell Detected |

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
