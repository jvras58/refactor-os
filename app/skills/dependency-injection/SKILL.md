---
name: dependency-injection
description: Aplicar Dependency Injection para refatorar Tight Coupling (dependências concretas instanciadas no __init__). Inclui exemplo canônico com factory default preservando a API pública.
---

# Dependency Injection — guia de aplicação

**Smell alvo:** Tight Coupling (dependências hardcoded, instanciadas dentro do consumidor).

## Intenção
Receber colaboradores via construtor ou parâmetro em vez de instanciá-los internamente,
permitindo substituição, testabilidade e desacoplamento da implementação concreta.

## Estrutura canônica
- (Opcional) Definir um `Protocol` ou ABC para o colaborador.
- Receber a dependência no `__init__` (constructor injection) ou em parâmetros (method injection).
- O cliente externo ("composition root") instancia e injeta a implementação concreta.
- Quando a API original não recebia a dependência, oferecer um **factory default** que constrói
  a dependência concreta — assim o chamador antigo continua funcionando.

## Regras estritas
1. **NÃO** instanciar dependências concretas dentro da classe consumidora.
2. Depender da abstração (Protocol/ABC), não do detalhe.
3. Permitir mocks/fakes em testes.
4. **A API pública continua aceitando chamadas sem o argumento injetado** — use default `None`
   e construa internamente a dependência concreta quando necessário.

## Exemplo canônico (extraído do dataset)

### Antes (smell)
```python
import smtplib

class WelcomeEmailService:
    def __init__(self):
        # dependência hardcoded — impossível mockar / trocar
        self.smtp = smtplib.SMTP("smtp.example.com", 587)
        self.smtp.starttls()
        self.smtp.login("user", "pass")

    def send_welcome(self, user_email: str, name: str) -> None:
        body = f"Hello {name}, welcome!"
        self.smtp.sendmail("noreply@example.com", user_email, body)


def register(user_email: str, name: str) -> None:
    service = WelcomeEmailService()
    service.send_welcome(user_email, name)
```

### Depois (DI com factory default preservando a API)
```python
class WelcomeEmailService:
    def __init__(self, smtp) -> None:
        # dependência injetada — fácil de substituir por um fake nos testes
        self.smtp = smtp

    def send_welcome(self, user_email: str, name: str) -> None:
        body = f"Hello {name}, welcome!"
        self.smtp.sendmail("noreply@example.com", user_email, body)


def register(user_email: str, name: str, smtp=None) -> None:
    if smtp is None:
        smtp = _build_default_smtp()
    service = WelcomeEmailService(smtp)
    service.send_welcome(user_email, name)


def _build_default_smtp():
    import smtplib
    smtp = smtplib.SMTP("smtp.example.com", 587)
    smtp.starttls()
    smtp.login("user", "pass")
    return smtp
```

### Justificativa arquitetural
1. `WelcomeEmailService` deixou de instanciar `smtplib.SMTP` no `__init__` — agora recebe
   o cliente SMTP via construtor.
2. A função `register` ganhou um parâmetro opcional `smtp=None`; quando ausente, um factory
   privado `_build_default_smtp()` constrói o cliente concreto.
3. A API pública é **preservada**: `register(email, name)` continua funcionando exatamente
   como antes para chamadores existentes; testes podem agora passar um fake SMTP.

### Benefícios esperados
- Permite testes unitários sem rede (substituir SMTP por mock).
- Trocar provedor SMTP é uma mudança de uma linha no composition root.
- API pública inalterada — chamadores antigos continuam funcionando.
