# 3.1. Definição do Domínio Estrito (Enums)
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

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


# 3.2. Schemas de Comunicação
class SmellDetection(BaseModel):
    has_smell: bool = Field(description="Booleano indicando se algum bad smell do escopo foi encontrado.")
    smell_type: BadSmellType
    line_start: Optional[int] = Field(description="Linha inicial onde o smell começa no código original.", default=None)
    line_end: Optional[int] = Field(description="Linha final onde o smell termina no código original.", default=None)
    affected_snippet: Optional[str] = Field(description="Trecho exato do código que contém o problema.", default=None)
    reasoning: str = Field(description="Justificativa técnica detalhada sobre a identificação do bad smell.")

class RefactoringProposal(BaseModel):
    applied_pattern: DesignPatternType
    refactored_code: str = Field(description="O código-fonte completo refatorado aplicando o design pattern.")
    architectural_explanation: str = Field(description="Explicação passo a passo de como o pattern resolveu o bad smell.")
    expected_benefits: List[str] = Field(description="Lista de melhorias na manutenibilidade e coesão.")

class ReflectionReview(BaseModel):
    is_approved: bool = Field(description="True apenas se o código refatorado preservar a lógica de negócios e aplicar o pattern corretamente.")
    critique: str = Field(description="Feedback detalhado. Obrigatório se is_approved for False.")
    final_validated_code: Optional[str] = Field(description="O código refatorado aprovado.", default=None)
