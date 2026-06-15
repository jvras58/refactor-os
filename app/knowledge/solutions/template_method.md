---
title: Template Method — importadores com o mesmo esqueleto
smell: Duplicated Code
pattern: Template Method
---

# Template Method — exemplo de solução

Corpus de referência (autoral, distinto do dataset de avaliação). Guia a
refatoração de **Duplicated Code** com esqueleto algorítmico repetido.

## Problema (antes)

```python
class CsvImporter:
    def run(self, path):
        raw = open(path).read()            # ler
        rows = self._parse_csv(raw)        # parsear (varia)
        self._validate(rows)               # validar
        self._save(rows)                   # salvar

class JsonImporter:
    def run(self, path):
        raw = open(path).read()            # ler (igual)
        rows = self._parse_json(raw)       # parsear (varia)
        self._validate(rows)               # validar (igual)
        self._save(rows)                   # salvar (igual)
```

## Solução (depois)

```python
from abc import ABC, abstractmethod


class Importer(ABC):
    def run(self, path: str) -> None:
        # esqueleto fixo, definido uma única vez
        raw = self._read(path)
        rows = self._parse(raw)
        self._validate(rows)
        self._save(rows)

    def _read(self, path: str) -> str:
        with open(path) as fh:
            return fh.read()

    @abstractmethod
    def _parse(self, raw: str) -> list[dict]: ...

    def _validate(self, rows: list[dict]) -> None: ...
    def _save(self, rows: list[dict]) -> None: ...


class CsvImporter(Importer):
    def _parse(self, raw: str) -> list[dict]: ...


class JsonImporter(Importer):
    def _parse(self, raw: str) -> list[dict]: ...
```

## Regras aplicadas
- O fluxo de alto nível (`run`) vive uma única vez na classe base.
- Só o passo que de fato varia (`_parse`) é um hook abstrato sobrescrito.
- Os passos idênticos (`_read`, `_validate`, `_save`) deixaram de ser duplicados.
