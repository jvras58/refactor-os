---
title: Builder/Parameter Object — configuração de requisição HTTP
smell: Long Parameter List
pattern: Builder/Parameter Object
---

# Builder/Parameter Object — exemplo de solução

Corpus de referência (autoral, distinto do dataset de avaliação). Guia a
refatoração de **Long Parameter List**.

## Problema (antes)

```python
def send_request(url, method, headers, body, timeout, retries, verify_ssl):
    ...
```

## Solução (depois)

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestConfig:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    timeout: float = 30.0
    retries: int = 0
    verify_ssl: bool = True


def send_request(config: RequestConfig):
    ...


# Wrapper fino mantém a assinatura antiga estável, se houver chamadores legados:
def send_request_legacy(url, method, headers, body, timeout, retries, verify_ssl):
    return send_request(
        RequestConfig(url, method, headers, body, timeout, retries, verify_ssl)
    )
```

## Regras aplicadas
- Parâmetros coesos agrupados num objeto imutável (`frozen=True`).
- Defaults preservam o comportamento original.
- Quando há chamadores existentes, um wrapper fino mantém a API pública estável.
