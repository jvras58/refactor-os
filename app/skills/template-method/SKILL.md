---
name: template-method
description: Aplicar Template Method para refatorar Duplicated Code (classes/funções com mesmo esqueleto e passos variáveis). Inclui exemplo canônico onde subclasses preservam a API pública.
---

# Template Method — guia de aplicação

**Smell alvo:** Duplicated Code (variações algorítmicas com mesmo esqueleto).

## Intenção
Definir o esqueleto de um algoritmo em uma classe base e delegar passos variáveis para
subclasses, eliminando duplicação entre fluxos parecidos.

## Estrutura canônica
- **Classe base abstrata** com o `template_method` que orquestra o fluxo de alto nível.
- **Hooks abstratos** (`_collect`, `_serialize`, `_finalize`) que subclasses sobrescrevem.
- **Subclasses** só implementam os passos divergentes.

## Regras estritas
1. O fluxo de alto nível deve permanecer inalterado.
2. Extrair APENAS os trechos que de fato divergem entre cópias.
3. Hooks devem ter assinatura clara (com type hints).
4. **A API pública das subclasses deve ser preservada** — `CSVReport.generate(rows)` continua
   funcionando da mesma forma, só que herda o esqueleto da base.

## Exemplo canônico (extraído do dataset)

### Antes (smell — três classes repetem validar → serializar → encode)
```python
class CSVReportGenerator:
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
        headers = list(rows[0].keys())
        body = ",".join(headers) + "\n"
        for row in rows:
            body += ",".join(str(row[h]) for h in headers) + "\n"
        return body.encode("utf-8")


class JSONReportGenerator:
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
        import json
        body = json.dumps(rows)
        return body.encode("utf-8")


class HTMLReportGenerator:
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
        headers = list(rows[0].keys())
        body = "<table>...</table>"
        return body.encode("utf-8")
```

### Depois (Template Method)
```python
from abc import ABC, abstractmethod


class ReportGenerator(ABC):
    def generate(self, rows: list[dict]) -> bytes:
        if not rows:
            raise ValueError("empty rows")
        return self._serialize(rows).encode("utf-8")

    @abstractmethod
    def _serialize(self, rows: list[dict]) -> str: ...


class CSVReportGenerator(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        headers = list(rows[0].keys())
        body = ",".join(headers) + "\n"
        for row in rows:
            body += ",".join(str(row[h]) for h in headers) + "\n"
        return body


class JSONReportGenerator(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        import json
        return json.dumps(rows)


class HTMLReportGenerator(ReportGenerator):
    def _serialize(self, rows: list[dict]) -> str:
        headers = list(rows[0].keys())
        body = "<table>...</table>"
        return body
```

### Justificativa arquitetural
1. O esqueleto comum (validar → serializar → encode) subiu para a base abstrata
   `ReportGenerator.generate`.
2. Cada subclasse implementa apenas o passo variável `_serialize`.
3. A API pública (`.generate(rows) -> bytes`) é preservada nas três subclasses.
4. Novos formatos (XML, YAML) entram só adicionando uma subclasse — não há mais
   risco de esquecer a validação ou o encode.

### Benefícios esperados
- Elimina duplicação do esqueleto validação+encode entre as 3 classes.
- Hook único de extensão (`_serialize`) por formato.
- API pública preservada nas subclasses existentes — código chamador inalterado.
