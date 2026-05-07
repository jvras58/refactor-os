"""Spec-driven communication schemas exchanged between the agents."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BadSmellType(str, Enum):
    COMPLEX_SWITCH = "Complex/Long Switch Statements"
    LONG_PARAMETER = "Long Parameter List"
    GOD_CLASS = "God Class"
    TIGHT_COUPLING = "Tight Coupling"
    DUPLICATED_CODE = "Duplicated Code"
    NO_SMELL = "No Smell Detected"


class DesignPatternType(str, Enum):
    STRATEGY = "Strategy Pattern"
    BUILDER = "Builder/Parameter Object"
    FACADE_SRP = "Facade/SRP"
    DEPENDENCY_INJECTION = "Dependency Injection"
    TEMPLATE_METHOD = "Template Method"
    NONE = "None"


SMELL_TO_PATTERN: dict[BadSmellType, DesignPatternType] = {
    BadSmellType.COMPLEX_SWITCH: DesignPatternType.STRATEGY,
    BadSmellType.LONG_PARAMETER: DesignPatternType.BUILDER,
    BadSmellType.GOD_CLASS: DesignPatternType.FACADE_SRP,
    BadSmellType.TIGHT_COUPLING: DesignPatternType.DEPENDENCY_INJECTION,
    BadSmellType.DUPLICATED_CODE: DesignPatternType.TEMPLATE_METHOD,
    BadSmellType.NO_SMELL: DesignPatternType.NONE,
}


class SmellDetection(BaseModel):
    has_smell: bool = Field(description="Indica se algum bad smell do escopo foi encontrado.")
    smell_type: BadSmellType
    line_start: Optional[int] = Field(default=None, description="Linha inicial do smell.")
    line_end: Optional[int] = Field(default=None, description="Linha final do smell.")
    affected_snippet: Optional[str] = Field(default=None, description="Trecho exato do problema.")
    reasoning: str = Field(description="Justificativa técnica detalhada da identificação.")


class RefactoringProposal(BaseModel):
    applied_pattern: DesignPatternType
    refactored_code: str = Field(description="Código-fonte completo refatorado.")
    architectural_explanation: str = Field(description="Como o pattern resolveu o smell.")
    expected_benefits: List[str] = Field(description="Melhorias esperadas em manutenibilidade/coesão.")


class ReflectionReview(BaseModel):
    is_approved: bool = Field(description="True apenas se preserva lógica e aplica o pattern corretamente.")
    critique: str = Field(description="Feedback detalhado. Obrigatório se is_approved=False.")
    final_validated_code: Optional[str] = Field(default=None, description="Código aprovado.")


class RefactorRequest(BaseModel):
    source_code: str = Field(description="Código-fonte original a ser analisado.")
    file_name: Optional[str] = Field(default=None, description="Nome opcional do arquivo de origem.")


class RefactorResult(BaseModel):
    detection: SmellDetection
    proposal: Optional[RefactoringProposal] = None
    review: Optional[ReflectionReview] = None
    iterations: int = Field(default=0, description="Iterações de reflection executadas.")
    approved: bool = False


class GroundTruthEntry(BaseModel):
    file: str
    smell_type: BadSmellType
    expected_pattern: DesignPatternType
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class EvaluationMetrics(BaseModel):
    total: int
    detector_precision: float
    detector_recall: float
    refactor_accuracy: float
    per_file: List[dict]
