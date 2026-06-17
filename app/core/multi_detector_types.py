"""Type vocabulary for the new multi-smell/multi-pattern detector.

Deliberately independent from ``app.core.schemas.BadSmellType``/``DesignPatternType``:
this detector drops Tight Coupling/Dependency Injection (out of scope per dataset_2)
and uses the renamed labels ("Builder", "Facade") that the production enums don't
have yet. Keeping this vocabulary local avoids touching the production schema while
the new detector is built and evaluated in isolation.
"""
from __future__ import annotations

from enum import StrEnum


class SmellType(StrEnum):
    COMPLEX_SWITCH = "Complex/Long Switch Statements"
    LONG_PARAMETER = "Long Parameter List"
    GOD_CLASS = "God Class"
    DUPLICATED_CODE = "Duplicated Code"


class PatternType(StrEnum):
    STRATEGY = "Strategy Pattern"
    BUILDER = "Builder"
    FACADE = "Facade"
    TEMPLATE_METHOD = "Template Method"


SMELL_TO_PATTERN: dict[SmellType, PatternType] = {
    SmellType.COMPLEX_SWITCH: PatternType.STRATEGY,
    SmellType.LONG_PARAMETER: PatternType.BUILDER,
    SmellType.GOD_CLASS: PatternType.FACADE,
    SmellType.DUPLICATED_CODE: PatternType.TEMPLATE_METHOD,
}

PATTERN_TO_SMELL: dict[PatternType, SmellType] = {
    pattern: smell for smell, pattern in SMELL_TO_PATTERN.items()
}
