# Builder / Parameter Object

**Smell alvo:** Long Parameter List (>= 5 parâmetros).

## Intenção
Agregar parâmetros relacionados em um único objeto coeso (Parameter Object) ou
construí-los gradualmente via Builder fluente.

## Estrutura
- `dataclass`/`BaseModel` agrupando campos relacionados.
- (Opcional) `Builder` com métodos `with_x(...)` e `build()`.
- Função alvo passa a receber UM parâmetro tipado em vez de N argumentos posicionais.

## Quando aplicar
- Função/método com 5+ parâmetros.
- Conjuntos de argumentos passados juntos por toda a base de código.
- Necessidade de validação centralizada.

## Exemplo (Python)
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ReportParams:
    start_date: str
    end_date: str
    user_id: int
    include_archived: bool = False
    format: str = "pdf"

def generate_report(params: ReportParams) -> bytes:
    ...
```

## Regras estritas
1. Agrupar apenas parâmetros coesos (mesma responsabilidade).
2. Preferir imutabilidade (`frozen=True`).
3. Validar no construtor quando aplicável.
