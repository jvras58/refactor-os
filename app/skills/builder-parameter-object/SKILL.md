---
name: builder-parameter-object
description: Aplicar Builder/Parameter Object para refatorar Long Parameter List (funções com 5+ parâmetros). Inclui exemplo canônico com wrapper preservando a assinatura pública original.
---

# Builder / Parameter Object — guia de aplicação

**Smell alvo:** Long Parameter List (>= 5 parâmetros).

## Intenção
Agregar parâmetros relacionados em um único objeto coeso (Parameter Object) ou construí-los
gradualmente via Builder fluente.

## Estrutura canônica
- **`@dataclass`** (ou `BaseModel`) agrupando campos relacionados.
- Método `build()` (opcional) que produz a saída esperada.
- Função alvo passa a receber UM parâmetro tipado em vez de N argumentos posicionais —
  **mas o wrapper original continua existindo** para preservar a API pública.

## Regras estritas
1. Agrupar apenas parâmetros coesos (mesma responsabilidade).
2. Preferir imutabilidade (`@dataclass(frozen=True)` quando viável).
3. Validar no construtor quando aplicável.
4. **A função/método público original deve continuar funcionando** — implemente como wrapper
   fino que constrói o objeto internamente e delega.

## Exemplo canônico (extraído do dataset)

### Antes (smell)
```python
def create_invoice(
    customer_id: int,
    customer_name: str,
    customer_email: str,
    billing_address: str,
    shipping_address: str,
    items: list,
    discount: float,
    tax_rate: float,
    currency: str,
    due_date: str,
) -> dict:
    subtotal = sum(item["price"] * item["qty"] for item in items)
    total = (subtotal - discount) * (1 + tax_rate)
    return {
        "customer": {"id": customer_id, "name": customer_name, "email": customer_email},
        "billing_address": billing_address,
        "shipping_address": shipping_address,
        "items": items,
        "total": total,
        "currency": currency,
        "due_date": due_date,
    }
```

### Depois (Parameter Object + wrapper preservando API)
```python
from dataclasses import dataclass

@dataclass
class InvoiceData:
    customer_id: int
    customer_name: str
    customer_email: str
    billing_address: str
    shipping_address: str
    items: list
    discount: float
    tax_rate: float
    currency: str
    due_date: str

    def build(self) -> dict:
        subtotal = sum(item["price"] * item["qty"] for item in self.items)
        total = (subtotal - self.discount) * (1 + self.tax_rate)
        return {
            "customer": {
                "id": self.customer_id,
                "name": self.customer_name,
                "email": self.customer_email,
            },
            "billing_address": self.billing_address,
            "shipping_address": self.shipping_address,
            "items": self.items,
            "total": total,
            "currency": self.currency,
            "due_date": self.due_date,
        }


def create_invoice(
    customer_id, customer_name, customer_email, billing_address, shipping_address,
    items, discount, tax_rate, currency, due_date,
) -> dict:
    return InvoiceData(
        customer_id, customer_name, customer_email, billing_address, shipping_address,
        items, discount, tax_rate, currency, due_date,
    ).build()
```

### Justificativa arquitetural
1. Parâmetros coesos do "domínio de fatura" foram agrupados em `InvoiceData`.
2. A lógica de cálculo migrou para `.build()` — o dataclass virou ponto único de validação futura.
3. A função pública `create_invoice` foi mantida byte-a-byte na assinatura;
   internamente delega para `InvoiceData(...).build()`.

### Benefícios esperados
- Reduz a aridade visível das chamadas internas (passa-se `InvoiceData` em vez de 10 args).
- Tipagem coesa permite IDE/IntelliSense melhor.
- API pública inalterada — nenhum chamador externo quebra.
