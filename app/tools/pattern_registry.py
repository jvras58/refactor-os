"""Strict registry of the 5 supported Design Patterns (anti-hallucination)."""
from __future__ import annotations

from typing import Any

from agno.tools import tool

DESIGN_PATTERNS: dict[str, dict[str, Any]] = {
    "Strategy Pattern": {
        "intent": "Encapsular famílias de algoritmos intercambiáveis em classes polimórficas.",
        "applies_to": "Complex/Long Switch Statements",
        "structure": [
            "Interface/ABC `Strategy` com método único.",
            "Classes concretas implementando cada branch do switch.",
            "Cliente/Context recebe `Strategy` por composição (injetada).",
        ],
        "rules": [
            "Cada `case` do switch original vira UMA classe concreta.",
            "Eliminar o switch substituindo por dispatch polimórfico.",
            "Nenhuma regra de negócio dos cases pode ser perdida.",
        ],
    },
    "Builder/Parameter Object": {
        "intent": "Reduzir Long Parameter List criando um objeto agregador imutável ou um builder fluente.",
        "applies_to": "Long Parameter List",
        "structure": [
            "Classe `Params`/`Config` (dataclass) agregando parâmetros relacionados.",
            "Opcional: `Builder` com métodos fluentes (`with_x`) para construção.",
            "Função alvo passa a receber UM único `Params`.",
        ],
        "rules": [
            "Agrupe apenas parâmetros coesos.",
            "Mantenha a assinatura pública estável onde possível (ou ofereça wrapper).",
        ],
    },
    "Facade/SRP": {
        "intent": "Quebrar uma God Class aplicando Single Responsibility Principle e expor uma Facade fina.",
        "applies_to": "God Class",
        "structure": [
            "Identificar responsabilidades distintas dentro da classe.",
            "Extrair cada responsabilidade em uma classe coesa dedicada.",
            "Manter uma `Facade` com a API pública orquestrando as classes extraídas.",
        ],
        "rules": [
            "Cada classe extraída deve ter uma única razão para mudar.",
            "A Facade não pode reintroduzir a God Class.",
        ],
    },
    "Dependency Injection": {
        "intent": "Eliminar dependências hardcoded recebendo colaboradores via construtor/parâmetro.",
        "applies_to": "Tight Coupling",
        "structure": [
            "Definir interface/Protocol para o colaborador.",
            "Receber a dependência no `__init__` (ou parâmetro de função).",
            "Cliente externo cria e injeta a implementação concreta.",
        ],
        "rules": [
            "Não instanciar dependência concreta dentro da classe.",
            "Permitir substituição em testes (mock/fake).",
        ],
    },
    "Template Method": {
        "intent": "Eliminar duplicação algorítmica extraindo o esqueleto e parametrizando os passos variáveis.",
        "applies_to": "Duplicated Code",
        "structure": [
            "Classe base abstrata com o `template_method` final.",
            "Métodos `hook` abstratos para os passos que variam.",
            "Subclasses sobrescrevem apenas os hooks.",
        ],
        "rules": [
            "Manter o fluxo de alto nível inalterado.",
            "Extrair APENAS as partes que de fato divergem.",
        ],
    },
}


_ALIASES = {
    "strategy": "Strategy Pattern",
    "builder": "Builder/Parameter Object",
    "parameter object": "Builder/Parameter Object",
    "facade": "Facade/SRP",
    "srp": "Facade/SRP",
    "facade/srp": "Facade/SRP",
    "dependency injection": "Dependency Injection",
    "di": "Dependency Injection",
    "template method": "Template Method",
}


def _resolve(name: str) -> str | None:
    if name in DESIGN_PATTERNS:
        return name
    return _ALIASES.get(name.strip().lower())


def lookup_pattern(pattern_name: str) -> dict[str, Any]:
    canonical = _resolve(pattern_name)
    if canonical is None:
        return {
            "error": "pattern not supported",
            "supported": sorted(DESIGN_PATTERNS.keys()),
        }
    return {"name": canonical, **DESIGN_PATTERNS[canonical]}


@tool(
    name="design_pattern_reference_tool",
    description=(
        "Retorna a estrutura canônica e regras estritas de UM dos 5 design patterns suportados: "
        "Strategy Pattern, Builder/Parameter Object, Facade/SRP, Dependency Injection, Template Method."
    ),
)
def design_pattern_reference_tool(pattern_name: str) -> dict[str, Any]:
    return lookup_pattern(pattern_name)
