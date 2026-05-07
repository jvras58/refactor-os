# Strategy Pattern

**Smell alvo:** Complex/Long Switch Statements.

## Intenção
Encapsular uma família de algoritmos em classes intercambiáveis, eliminando estruturas
condicionais complexas (`switch`, longas cadeias de `if/elif`) por dispatch polimórfico.

## Estrutura
- `Strategy` (interface/ABC) define a operação única.
- `ConcreteStrategyA`, `ConcreteStrategyB`, ... implementam cada branch do switch original.
- `Context` recebe uma instância de `Strategy` por composição e delega a execução.

## Quando aplicar
- Cada `case` representa uma variação algorítmica coesa.
- Os cases tendem a crescer com novas regras.
- Você precisa testar cada variação isoladamente.

## Exemplo (Python)
```python
from abc import ABC, abstractmethod

class TaxStrategy(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float: ...

class BrazilTax(TaxStrategy):
    def calculate(self, amount: float) -> float:
        return amount * 0.27

class USTax(TaxStrategy):
    def calculate(self, amount: float) -> float:
        return amount * 0.20

class TaxContext:
    def __init__(self, strategy: TaxStrategy) -> None:
        self.strategy = strategy
    def total(self, amount: float) -> float:
        return amount + self.strategy.calculate(amount)
```

## Regras estritas
1. Cada branch original vira UMA classe concreta.
2. Nenhuma regra de negócio dos cases pode ser perdida.
3. O switch deve desaparecer; o cliente passa a depender da abstração `Strategy`.
