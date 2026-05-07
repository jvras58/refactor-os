# Dependency Injection

**Smell alvo:** Tight Coupling (dependências hardcoded).

## Intenção
Receber colaboradores via construtor ou parâmetro, em vez de instanciá-los internamente,
permitindo substituição, testabilidade e desacoplamento da implementação concreta.

## Estrutura
- Definir `Protocol`/ABC para o colaborador.
- Receber a dependência no `__init__` (constructor injection) ou em parâmetros (method injection).
- O cliente externo (composition root) instancia e injeta a implementação concreta.

## Exemplo (Python)
```python
from typing import Protocol

class Mailer(Protocol):
    def send(self, to: str, body: str) -> None: ...

class SMTPMailer:
    def send(self, to: str, body: str) -> None: ...

class NotificationService:
    def __init__(self, mailer: Mailer) -> None:
        self.mailer = mailer

    def notify(self, user_email: str) -> None:
        self.mailer.send(user_email, "Hello")
```

## Regras estritas
1. NÃO instanciar dependências concretas dentro da classe consumidora.
2. Depender da abstração (Protocol/ABC), não do detalhe.
3. Permitir mocks/fakes em testes.
