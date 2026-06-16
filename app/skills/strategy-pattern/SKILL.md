---
name: strategy-pattern
description: Aplicar Strategy Pattern para refatorar Complex/Long Switch Statements (cadeias de if/elif ou match/case que despacham por valor). Inclui exemplo canônico com preservação da API pública.
---

# Strategy Pattern — guia de aplicação

**Smell alvo:** Complex/Long Switch Statements.

## Intenção
Encapsular uma família de algoritmos em estratégias intercambiáveis, eliminando estruturas
condicionais complexas (`switch`, longas cadeias de `if/elif`) por dispatch polimórfico.

## Estrutura canônica
- **Strategy** (interface/ABC ou tipo `Callable`) define a operação única.
- **ConcreteStrategyA, ConcreteStrategyB, ...** implementam cada branch do switch original.
- **Context** recebe a estratégia por composição (ou usa um dicionário `dict[str, Strategy]`)
  e delega a execução.

## Regras estritas
1. Cada branch original vira UMA estratégia (classe concreta ou função).
2. Nenhuma regra de negócio dos cases pode ser perdida.
3. O switch desaparece; o cliente passa a depender da abstração `Strategy` ou do lookup.
4. **A assinatura pública original deve ser preservada** — o código chamador continua igual.
5. O caso default (ex.: `raise ValueError`) é mantido quando a chave não existe no lookup.

## Exemplo canônico (extraído do dataset)

### Antes (smell)
```python
def calculate_shipping(country, weight_kg):
    if country == "BR":
        return 15.0 if weight_kg < 1 else 35.0
    elif country == "US":
        return 10.0 if weight_kg < 1 else 25.0
    elif country == "DE":
        return 12.0 if weight_kg < 1 else 28.0
    else:
        raise ValueError(country)
```

### Depois (Strategy aplicado)
```python
from collections.abc import Callable

_STRATEGIES: dict[str, Callable[[float], float]] = {
    "BR": lambda w: 15.0 if w < 1 else 35.0,
    "US": lambda w: 10.0 if w < 1 else 25.0,
    "DE": lambda w: 12.0 if w < 1 else 28.0,
}

def calculate_shipping(country, weight_kg):
    strategy = _STRATEGIES.get(country)
    if strategy is None:
        raise ValueError(country)
    return strategy(weight_kg)
```

### Justificativa arquitetural (template do `architectural_explanation`)
1. Cada ramo do switch vira uma estratégia indexada pela chave de despacho.
2. A função pública vira um dispatcher que olha o dicionário e delega.
3. O default (`ValueError`) é preservado quando a chave não existe.
4. Adicionar uma nova chave é alterar o dicionário, sem editar a função.

### Benefícios esperados
- Aberto para extensão, fechado para modificação (princípio OCP).
- Despacho O(1) via dicionário, sem cadeia de elif.
- API pública (assinatura de `calculate_shipping`) inalterada.
