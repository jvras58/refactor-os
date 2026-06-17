"""Spec-driven communication schemas exchanged between the agents.

Type vocabulary (4 smells + 4 patterns) and the detection schemas come from the
multi-detector pipeline: detection is multi-label — phase 2 produces one
``SmellHeuristicSignal`` per smell, phase 3 one ``TypeDetectionResult`` per
smell/pattern type, aggregated into a ``DetectionScanResult``.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


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

#: Every type name the detector decides on — 4 smells + 4 patterns, in scan order.
ALL_TYPE_NAMES: tuple[str, ...] = tuple(s.value for s in SmellType) + tuple(
    p.value for p in PatternType
)


# --------------------------------------------------------------------- detection
class SmellHeuristicSignal(BaseModel):
    """Deterministic AST-only signal for a single smell — always present per smell,
    even when the heuristic found nothing (``possible=False, score=0.0``)."""

    smell_type: SmellType
    possible: bool
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    line_start: int | None = None
    line_end: int | None = None


class HeuristicScan(BaseModel):
    """One ``SmellHeuristicSignal`` per in-scope smell (phase 2 output)."""

    signals: dict[SmellType, SmellHeuristicSignal]


class TypeEvidence(BaseModel):
    """A single location backing a smell/pattern detection."""

    local: str = Field(description="Nome da classe/método (ex.: 'Pedido.criar') ou '<módulo>'.")
    linhas: list[int] = Field(description="[linha_inicial, linha_final] do trecho evidenciado.")


class TypeDetectionResult(BaseModel):
    """LLM verdict for ONE smell or pattern type — also the output schema of a
    single phase-3 LLM call (one type checked per call, 8 calls total)."""

    type_name: str = Field(description="Nome exato do smell ou pattern avaliado nesta chamada.")
    detected: bool
    evidencias: list[TypeEvidence] = Field(default_factory=list)
    reasoning: str = Field(description="Justificativa técnica da decisão.")


class DetectionScanResult(BaseModel):
    """Raw output of detection phases 1-3 — everything checked, both detected and not.

    Phase 4 compilers consume this to produce whatever shape a downstream
    consumer needs (see ``ResultCompiler`` in the service module).
    """

    heuristic_scan: HeuristicScan
    type_results: list[TypeDetectionResult]

    def detected_names(self) -> list[str]:
        """Names of every detected smell/pattern, in scan order."""
        return [result.type_name for result in self.type_results if result.detected]


# --------------------------------------------------------------------- pipeline
class RefactoringProposal(BaseModel):
    applied_pattern: PatternType
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
    detection: DetectionScanResult | None = Field(
        default=None, description="Scan completo do detector (None se a detecção falhou)."
    )
    detected_problems: list[str] = Field(
        default_factory=list, description="Smells/patterns detectados (fase 4 compilada)."
    )
    target_smell: SmellType | None = Field(
        default=None, description="Smell escolhido como alvo da refatoração."
    )
    target_pattern: PatternType | None = Field(
        default=None, description="Pattern aplicado pelo Recommender para o alvo."
    )
    proposal: RefactoringProposal | None = None
    review: ReflectionReview | None = None
    iterations: int = Field(default=0, description="Iterações de reflection executadas.")
    approved: bool = False
    error: str | None = Field(default=None, description="Mensagem de erro se o pipeline falhou.")


# --------------------------------------------------------------------- evaluation
class GroundTruthEntry(BaseModel):
    """One labeled example of ``ground_truth_detector.json`` — multi-label."""

    file: str = Field(description="Caminho do exemplo relativo a dataset/examples/.")
    problems: list[str] = Field(
        default_factory=list,
        description="Smells/patterns presentes no arquivo (vazio = código limpo).",
    )


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
    """Agente Rastreador — avaliação multi-label sobre pares (arquivo, tipo).

    Cada arquivo gera 8 decisões binárias (4 smells + 4 patterns); a matriz de
    confusão agrega todas elas.
    - false_negative: o tipo estava presente mas o detector não o marcou.
    - false_positive: o detector marcou um tipo que não estava presente.
    """

    total_files: int
    confusion: ConfusionMatrix
    precision: float
    recall: float
    accuracy: float
    f1: float
    specificity: float
    false_positive_rate: float
    false_negative_rate: float
    exact_match_rate: float = Field(
        description="Fração de arquivos cujo conjunto detectado bate exatamente com o esperado."
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
    expected_problems: list[str] = Field(
        default_factory=list,
        description="Smells/patterns presentes no código (vazio = código limpo).",
    )
    name: str | None = Field(default=None, description="Rótulo opcional para identificar a amostra nos relatórios.")


class RefactorEvalSample(BaseModel):
    """Amostra rotulada para avaliar o Refatorador com código submetido pelo usuário."""

    source_code: str = Field(min_length=1, max_length=50_000)
    expected_pattern: PatternType
    expected_smell: SmellType | None = None
    name: str | None = Field(default=None, description="Rótulo opcional para identificar a amostra nos relatórios.")


class CriticEvalSample(BaseModel):
    """Amostra rotulada para avaliar o Critic com código submetido pelo usuário."""

    problem_code: str = Field(min_length=1, max_length=50_000)
    solution_code: str = Field(min_length=1, max_length=50_000)
    applied_pattern: PatternType
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
    """Body do POST /evaluate/critic. O dataset atual não traz soluções rotuladas
    para o Critic, então ``samples`` é obrigatório na prática."""

    samples: list[CriticEvalSample] | None = None


class FullEvalRequest(BaseModel):
    """Body opcional do POST /evaluate/all.

    Cada seção é independente: ausente/vazia → o agente roda sobre o dataset;
    com ``samples`` → roda sobre o código submetido. Permite misturar (ex.:
    Detector ad-hoc + Refatorador e Revisor sobre o dataset).
    """

    detector: DetectorEvalRequest | None = None
    refactor: RefactorEvalRequest | None = None
    critic: CriticEvalRequest | None = None
