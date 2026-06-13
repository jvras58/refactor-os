---
title: Dependency Injection — gateway de notificação hardcoded
smell: Tight Coupling
pattern: Dependency Injection
---

# Dependency Injection — exemplo de solução

Corpus de referência (autoral, distinto do dataset de avaliação). Guia a
refatoração de **Tight Coupling**.

## Problema (antes)

```python
class OrderNotifier:
    def __init__(self):
        # dependência concreta criada dentro da classe — impossível trocar/mockar
        self.gateway = TwilioGateway(api_key="hardcoded")

    def notify(self, order_id: str, phone: str) -> None:
        self.gateway.send(phone, f"Order {order_id} confirmed")
```

## Solução (depois)

```python
from typing import Protocol


class SmsGateway(Protocol):
    def send(self, to: str, body: str) -> None: ...


class OrderNotifier:
    def __init__(self, gateway: SmsGateway) -> None:
        # colaborador injetado via construtor
        self._gateway = gateway

    def notify(self, order_id: str, phone: str) -> None:
        self._gateway.send(phone, f"Order {order_id} confirmed")


# Composição na borda da aplicação:
# notifier = OrderNotifier(TwilioGateway(api_key=settings.twilio_key))
```

## Regras aplicadas
- A dependência deixou de ser instanciada dentro da classe.
- Um `Protocol` define o contrato, permitindo fakes/mocks em teste.
- A criação da implementação concreta sobe para o cliente (composition root).
