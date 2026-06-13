# Facade / SRP

**Smell alvo:** God Class (baixa coesão, > 20 membros).

## Intenção
Quebrar uma classe monolítica em colaboradores especializados (SRP) e oferecer uma
Facade fina para preservar a API pública.

## Estrutura
- Identificar agrupamentos coesos de métodos/atributos por responsabilidade.
- Extrair cada grupo para uma classe dedicada.
- Manter uma `Facade` que orquestra os colaboradores e expõe a interface pública estável.

## Exemplo (Python)
```python
class UserRepository:
    def find(self, user_id: int): ...
    def save(self, user): ...

class EmailNotifier:
    def send_welcome(self, user): ...

class AuditLog:
    def record(self, event: str, user): ...

class UserService:  # Facade
    def __init__(self, repo: UserRepository, notifier: EmailNotifier, audit: AuditLog) -> None:
        self.repo, self.notifier, self.audit = repo, notifier, audit

    def register(self, user) -> None:
        self.repo.save(user)
        self.notifier.send_welcome(user)
        self.audit.record("user.registered", user)
```

## Regras estritas
1. Cada classe extraída tem UMA razão para mudar.
2. A Facade não pode reintroduzir comportamento das classes extraídas.
3. Preservar a API pública sempre que possível.