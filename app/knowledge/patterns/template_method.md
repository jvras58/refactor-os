# Template Method

**Smell alvo:** Duplicated Code (variações algorítmicas).

## Intenção
Definir o esqueleto de um algoritmo em uma classe base e delegar passos variáveis para
subclasses, eliminando duplicação entre fluxos parecidos.

## Estrutura
- Classe base abstrata com o `template_method` final que orquestra o fluxo.
- Hooks abstratos (`_prepare`, `_process`, `_finalize`) que subclasses sobrescrevem.
- Subclasses só implementam os passos divergentes.

## Exemplo (Python)
```python
from abc import ABC, abstractmethod

class ReportGenerator(ABC):
    def generate(self) -> bytes:        # template method
        data = self._collect()
        body = self._render(data)
        return self._export(body)

    @abstractmethod
    def _collect(self) -> dict: ...

    @abstractmethod
    def _render(self, data: dict) -> str: ...

    def _export(self, body: str) -> bytes:
        return body.encode("utf-8")

class PDFReport(ReportGenerator):
    def _collect(self) -> dict: ...
    def _render(self, data: dict) -> str: ...
```

## Regras estritas
1. O fluxo de alto nível deve permanecer inalterado.
2. Extrair APENAS os trechos que de fato divergem entre cópias.
3. Hooks devem ter assinatura clara e documentada.