"""Spec-driven communication schemas exchanged between the agents."""
from enum import StrEnum

from pydantic import BaseModel, Field


class BadSmellType(StrEnum):
    COMPLEX_SWITCH = "Complex/Long Switch Statements"
    LONG_PARAMETER = "Long Parameter List"
    GOD_CLASS = "God Class"
    TIGHT_COUPLING = "Tight Coupling"
    DUPLICATED_CODE = "Duplicated Code"
    NO_SMELL = "No Smell Detected"


class DesignPatternType(StrEnum):
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
    line_start: int | None = Field(default=None, description="Linha inicial do smell.")
    line_end: int | None = Field(default=None, description="Linha final do smell.")
    affected_snippet: str | None = Field(default=None, description="Trecho exato do problema.")
    reasoning: str = Field(description="Justificativa técnica detalhada da identificação.")


class RefactoringProposal(BaseModel):
    applied_pattern: DesignPatternType
    refactored_code: str = Field(description="Código-fonte completo refatorado.")
    architectural_explanation: str = Field(description="Como o pattern resolveu o smell.")
    expected_benefits: list[str] = Field(description="Melhorias esperadas em manutenibilidade/coesão.")


class ReflectionReview(BaseModel):
    is_approved: bool = Field(description="True apenas se preserva lógica e aplica o pattern corretamente.")
    critique: str = Field(description="Feedback detalhado. Obrigatório se is_approved=False.")
    final_validated_code: str | None = Field(default=None, description="Código aprovado.")


class RefactorRequest(BaseModel):
    source_code: str = Field(
        description="Código-fonte original a ser analisado.",
        min_length=1,
        max_length=50_000,
    )
    file_name: str | None = Field(default=None, description="Nome opcional do arquivo de origem.")


class RefactorResult(BaseModel):
    detection: SmellDetection
    proposal: RefactoringProposal | None = None
    review: ReflectionReview | None = None
    iterations: int = Field(default=0, description="Iterações de reflection executadas.")
    approved: bool = False
    error: str | None = Field(default=None, description="Mensagem de erro se o pipeline falhou.")


class GroundTruthEntry(BaseModel):
    file: str
    smell_type: BadSmellType
    expected_pattern: DesignPatternType
    line_start: int | None = None
    line_end: int | None = None


class CriticTruthEntry(BaseModel):
    """Labeled solution fed to the Critic in isolation to measure its judgment."""

    solution_file: str = Field(description="Arquivo .py com o código refatorado a ser julgado.")
    problem_file: str = Field(description="Arquivo .py original que originou a refatoração.")
    applied_pattern: DesignPatternType = Field(description="Pattern que a solução declara aplicar.")
    expected_approved: bool = Field(
        description="Veredito correto: True se a solução é boa (Critic deveria aprovar)."
    )
    defect_kind: str | None = Field(
        default=None,
        description="Tipo do defeito quando expected_approved=False (ex.: syntax, logic, wrong_pattern).",
    )


class EvaluationMetrics(BaseModel):
    """Combined legacy report kept for backward compatibility with /api/v1/evaluate."""

    total: int
    detector_precision: float
    detector_recall: float
    refactor_accuracy: float
    per_file: list[dict]


class ConfusionMatrix(BaseModel):
    """Binary confusion matrix shared by Detector and Critic evaluations."""

    true_positive: int = 0
    false_positive: int = 0
    true_negative: int = 0
    false_negative: int = 0

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.true_negative + self.false_negative


class DetectorMetrics(BaseModel):
    """Agente Rastreador — mede Falsos Positivos e Falsos Negativos da detecção.

    Classe positiva = "o código contém um bad smell do escopo".
    - false_negative: código tem problema mas o agente disse que não tem (deixou passar).
    - false_positive: código está limpo mas o agente apontou um smell (viu onde não existe).
    """

    total: int
    confusion: ConfusionMatrix
    precision: float
    recall: float
    accuracy: float
    f1: float
    specificity: float
    false_positive_rate: float
    false_negative_rate: float
    type_accuracy: float = Field(
        description="Entre os arquivos com smell corretamente detectado, fração com o tipo de smell certo."
    )
    per_file: list[dict]


class RefactorQualityMetrics(BaseModel):
    """Agente Refatorador — precisão e qualidade da implementação proposta.

    Uma proposta é considerada correta quando aplica o pattern esperado, mantém sintaxe
    válida e preserva a lógica (assinaturas públicas e nº de ramos de controle).
    """

    total: int
    accuracy: float = Field(description="Fração de problemas cuja refatoração é totalmente correta.")
    pattern_accuracy: float
    syntax_valid_rate: float
    logic_preserved_rate: float
    pipeline_approved_rate: float
    avg_iterations: float
    per_file: list[dict]


class CriticMetrics(BaseModel):
    """Agente Revisor — confiabilidade do julgamento.

    Classe positiva = "a solução é correta" (o Critic deveria aprovar).
    - false_accept_rate: soluções incorretas que o Critic aprovou (disse que estava correta).
    - false_reject_rate: soluções corretas que o Critic reprovou (disse que estava incorreta).
    """

    total: int
    confusion: ConfusionMatrix
    accuracy: float
    precision: float
    recall: float
    f1: float
    false_accept_rate: float
    false_reject_rate: float
    per_file: list[dict]


class FullEvaluationReport(BaseModel):
    """Aggregates the three independent agent evaluations."""

    detector: DetectorMetrics
    refactor: RefactorQualityMetrics
    critic: CriticMetrics


class DetectorEvalSample(BaseModel):
    """Amostra rotulada para avaliar o Detector com código submetido pelo usuário."""

    source_code: str = Field(min_length=1, max_length=50_000)
    expected_smell: BadSmellType
    expected_pattern: DesignPatternType | None = None
    name: str | None = Field(default=None, description="Rótulo opcional para identificar a amostra nos relatórios.")


class RefactorEvalSample(BaseModel):
    """Amostra rotulada para avaliar o Refatorador com código submetido pelo usuário."""

    source_code: str = Field(min_length=1, max_length=50_000)
    expected_pattern: DesignPatternType
    expected_smell: BadSmellType | None = None
    name: str | None = Field(default=None, description="Rótulo opcional para identificar a amostra nos relatórios.")


class CriticEvalSample(BaseModel):
    """Amostra rotulada para avaliar o Critic com código submetido pelo usuário."""

    problem_code: str = Field(min_length=1, max_length=50_000)
    solution_code: str = Field(min_length=1, max_length=50_000)
    applied_pattern: DesignPatternType
    expected_approved: bool
    defect_kind: str | None = None
    name: str | None = Field(default=None, description="Rótulo opcional para identificar a amostra nos relatórios.")


class DetectorEvalRequest(BaseModel):
    """Body opcional do POST /evaluate/detector. Vazio → roda sobre o dataset."""

    samples: list[DetectorEvalSample] | None = None


class RefactorEvalRequest(BaseModel):
    """Body opcional do POST /evaluate/refactor. Vazio → roda sobre o dataset."""

    samples: list[RefactorEvalSample] | None = None


class CriticEvalRequest(BaseModel):
    """Body opcional do POST /evaluate/critic. Vazio → roda sobre o dataset."""

    samples: list[CriticEvalSample] | None = None
