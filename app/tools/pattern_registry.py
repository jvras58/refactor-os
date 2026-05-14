"""Strict registry of the 5 supported Design Patterns and smell-to-pattern mapping.

This module has two responsibilities:

1. Pattern reference:
   Given a design pattern name, return its canonical intent, structure and rules.

2. Smell mapping:
   Given a detected code smell, normalize it to the project scope and return
   the only allowed design pattern recommendation.

The second responsibility is important for the Recommender Agent because it
prevents the LLM from hallucinating patterns outside the 5 pairs defined in
the project scope.
"""
from __future__ import annotations

from typing import Any

from agno.tools import tool


class UnknownSmellError(ValueError):
    """Raised when a smell is outside the supported project scope."""


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


_PATTERN_ALIASES = {
    "strategy": "Strategy Pattern",
    "strategy pattern": "Strategy Pattern",
    "builder": "Builder/Parameter Object",
    "parameter object": "Builder/Parameter Object",
    "builder/parameter object": "Builder/Parameter Object",
    "facade": "Facade/SRP",
    "srp": "Facade/SRP",
    "facade/srp": "Facade/SRP",
    "dependency injection": "Dependency Injection",
    "di": "Dependency Injection",
    "template method": "Template Method",
}


# Raw labels accepted from the Detector Agent, Kaggle dataset labels,
# or manually curated ground truth.
#
# Value format:
#   raw smell label -> (canonical smell in project scope, canonical pattern)
_SMELL_TO_PATTERN: dict[str, tuple[str, str]] = {
    # Complex/Long Switch Statements -> Strategy Pattern
    "switch statements": (
        "Complex/Long Switch Statements",
        "Strategy Pattern",
    ),
    "complex/long switch statements": (
        "Complex/Long Switch Statements",
        "Strategy Pattern",
    ),
    "complex switch": (
        "Complex/Long Switch Statements",
        "Strategy Pattern",
    ),
    "long switch": (
        "Complex/Long Switch Statements",
        "Strategy Pattern",
    ),
    "type checking": (
        "Complex/Long Switch Statements",
        "Strategy Pattern",
    ),

    # Long Parameter List -> Builder/Parameter Object
    "long parameter list": (
        "Long Parameter List",
        "Builder/Parameter Object",
    ),
    "data clumps": (
        "Long Parameter List",
        "Builder/Parameter Object",
    ),
    "too many parameters": (
        "Long Parameter List",
        "Builder/Parameter Object",
    ),

    # God Class -> Facade/SRP
    "god class": (
        "God Class",
        "Facade/SRP",
    ),
    "large class": (
        "God Class",
        "Facade/SRP",
    ),
    "low cohesion": (
        "God Class",
        "Facade/SRP",
    ),

    # Tight Coupling -> Dependency Injection
    "tight coupling": (
        "Tight Coupling",
        "Dependency Injection",
    ),
    "hardcoded dependency": (
        "Tight Coupling",
        "Dependency Injection",
    ),
    "hardcoded dependencies": (
        "Tight Coupling",
        "Dependency Injection",
    ),
    "message chains": (
        "Tight Coupling",
        "Dependency Injection",
    ),
    "shotgun surgery": (
        "Tight Coupling",
        "Dependency Injection",
    ),

    # Duplicated Code -> Template Method
    "duplicated code": (
        "Duplicated Code",
        "Template Method",
    ),
    "duplicate code": (
        "Duplicated Code",
        "Template Method",
    ),
    "code duplication": (
        "Duplicated Code",
        "Template Method",
    ),
}


def _normalize_key(value: str) -> str:
    return value.strip().lower()


def _resolve(name: str) -> str | None:
    if name in DESIGN_PATTERNS:
        return name
    return _PATTERN_ALIASES.get(_normalize_key(name))


def lookup_pattern(pattern_name: str) -> dict[str, Any]:
    canonical = _resolve(pattern_name)
    if canonical is None:
        return {
            "error": "pattern not supported",
            "supported": sorted(DESIGN_PATTERNS.keys()),
        }
    return {"name": canonical, **DESIGN_PATTERNS[canonical]}


def normalize_smell(smell_type: str) -> str:
    """Normalize a raw smell label into one of the 5 project smell categories."""
    key = _normalize_key(smell_type)

    if key not in _SMELL_TO_PATTERN:
        raise UnknownSmellError(
            f"Unsupported smell type: {smell_type}. "
            f"Supported smell labels: {list_supported_smells()}"
        )

    normalized_smell, _ = _SMELL_TO_PATTERN[key]
    return normalized_smell


def resolve_pattern_for_smell(smell_type: str) -> dict[str, Any]:
    """Resolve a detected smell into the canonical pattern recommendation.

    This is the main deterministic function used by the Recommender Agent.

    Example:
        "Switch Statements" -> Strategy Pattern
        "Large Class" -> Facade/SRP
        "Data Clumps" -> Builder/Parameter Object
    """
    key = _normalize_key(smell_type)

    if key not in _SMELL_TO_PATTERN:
        raise UnknownSmellError(
            f"Unsupported smell type: {smell_type}. "
            f"Supported smell labels: {list_supported_smells()}"
        )

    normalized_smell, pattern_name = _SMELL_TO_PATTERN[key]
    pattern_reference = lookup_pattern(pattern_name)

    return {
        "input_smell": smell_type,
        "normalized_smell": normalized_smell,
        "recommended_pattern": pattern_name,
        "pattern_reference": pattern_reference,
    }


def list_supported_smells() -> list[str]:
    """Return all raw smell labels accepted by the registry."""
    return sorted(_SMELL_TO_PATTERN.keys())


@tool(
    name="design_pattern_reference_tool",
    description=(
        "Retorna a estrutura canônica e regras estritas de UM dos 5 design patterns suportados: "
        "Strategy Pattern, Builder/Parameter Object, Facade/SRP, Dependency Injection, Template Method."
    ),
)
def design_pattern_reference_tool(pattern_name: str) -> dict[str, Any]:
    return lookup_pattern(pattern_name)


@tool(
    name="smell_to_pattern_tool",
    description=(
        "Recebe um code smell detectado e retorna o smell normalizado e o único design pattern "
        "permitido dentro do escopo do projeto."
    ),
)
def smell_to_pattern_tool(smell_type: str) -> dict[str, Any]:
    return resolve_pattern_for_smell(smell_type)
