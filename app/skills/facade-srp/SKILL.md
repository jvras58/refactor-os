---
name: facade-srp
description: Aplicar Facade/SRP para refatorar God Class (classes monolíticas com 20+ membros e múltiplas responsabilidades). Inclui exemplo canônico onde a Facade preserva a API pública original.
---

# Facade / SRP — guia de aplicação

**Smell alvo:** God Class (baixa coesão, > 20 membros, > 1 responsabilidade).

## Intenção
Quebrar uma classe monolítica em colaboradores especializados (SRP) e oferecer uma Facade fina
que preserva a API pública original.

## Estrutura canônica
- Identificar **agrupamentos coesos** de métodos/atributos por responsabilidade.
- Extrair cada grupo para uma **classe dedicada** (Repository, Service, Notifier, AuditLog, ...).
- Manter a classe original como **Facade** que orquestra os colaboradores e **expõe a interface
  pública estável** — cada método público vira um delegate fino.

## Regras estritas
1. Cada classe extraída tem UMA razão para mudar (SRP).
2. A Facade não pode reintroduzir comportamento das classes extraídas.
3. **Preservar a API pública sempre que possível** — o método público antigo continua existindo
   na Facade e delega ao colaborador correto.
4. Atributos públicos críticos (ex.: listas que clientes externos podem ler) ficam na Facade.

## Exemplo canônico (extraído do dataset)

### Antes (smell — `OrderManager` com 4 responsabilidades misturadas)
```python
class OrderManager:
    def __init__(self):
        self.orders = []
        self.users = []
        self.inventory = {}
        self.audit_log = []

    def create_user(self, name, email): ...
    def update_user(self, idx, name): ...
    def delete_user(self, idx): ...
    def list_users(self): ...
    def add_inventory(self, sku, qty): ...
    def remove_inventory(self, sku, qty): ...
    def check_stock(self, sku): ...
    def reserve_stock(self, sku, qty): ...
    def create_order(self, user_idx, sku, qty): ...
    def cancel_order(self, idx): ...
    def list_orders(self): ...
    def send_email(self, to, body): ...
    def send_sms(self, to, body): ...
    def log(self, event, payload): ...
    def export_audit(self): ...
    def total_revenue(self): ...
    def report(self): ...
```

### Depois (Facade + colaboradores SRP)
```python
class UserRepository:
    def __init__(self): self.users = []
    def create(self, name, email): self.users.append({"name": name, "email": email})
    def list(self): return list(self.users)

class Inventory:
    def __init__(self): self.stock = {}
    def add(self, sku, qty): self.stock[sku] = self.stock.get(sku, 0) + qty
    def reserve(self, sku, qty):
        if self.stock.get(sku, 0) >= qty:
            self.stock[sku] -= qty
            return True
        return False

class Notifier:
    def email(self, to, body): print(f"Email -> {to}: {body}")
    def sms(self, to, body): print(f"SMS -> {to}: {body}")

class AuditLog:
    def __init__(self): self.entries = []
    def log(self, event, payload): self.entries.append({"event": event, "payload": payload})

class OrderManager:
    """Facade que coordena os colaboradores, preservando a API pública original."""
    def __init__(self):
        self.orders = []
        self._users = UserRepository()
        self._inventory = Inventory()
        self._notifier = Notifier()
        self._audit = AuditLog()

    def create_user(self, name, email): self._users.create(name, email)
    def list_users(self): return self._users.list()
    def add_inventory(self, sku, qty): self._inventory.add(sku, qty)
    def reserve_stock(self, sku, qty): return self._inventory.reserve(sku, qty)
    def send_email(self, to, body): self._notifier.email(to, body)
    def log(self, event, payload): self._audit.log(event, payload)
    # ... (cada método público antigo continua existindo, delegando para o colaborador)
```

### Justificativa arquitetural
1. Identifiquei 4 responsabilidades distintas no `OrderManager`: usuários, estoque,
   notificação e auditoria.
2. Extraí cada uma para uma classe dedicada com nome focado.
3. A classe original virou Facade — preserva todos os métodos públicos como delegates finos.
4. Atributo `self.orders` permaneceu na Facade por ser parte do estado público observável.

### Benefícios esperados
- Cada colaborador tem UMA razão para mudar (SRP).
- Possível testar `Inventory` ou `Notifier` em isolamento sem instanciar todo o `OrderManager`.
- API pública preservada — nenhum chamador externo quebra.
