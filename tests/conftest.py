"""Shared pytest fixtures for the test suite."""

import json
from pathlib import Path

import pytest

from app.core import config
from app.core.exceptions import InvalidPythonCodeError
from app.core.schemas import (
    ALL_TYPE_NAMES,
    DetectionScanResult,
    HeuristicScan,
    PatternType,
    RefactoringProposal,
    RefactorResult,
    ReflectionReview,
    SmellHeuristicSignal,
    SmellType,
    TypeDetectionResult,
)
from app.services.evaluation_service import EvaluationService

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def settings() -> config.Settings:
    return config.Settings(_env_file=None)


@pytest.fixture
def settings_factory(tmp_path):
    def _factory(**overrides) -> config.Settings:
        dataset_dir = overrides.pop("dataset_dir", tmp_path / "dataset")
        dataset_dir.mkdir(parents=True, exist_ok=True)
        return config.Settings(
            _env_file=None,
            dataset_dir=dataset_dir,
            **overrides,
        )

    return _factory


@pytest.fixture
def use_settings(monkeypatch):
    original_get_settings = config.get_settings

    def _apply(settings: config.Settings) -> config.Settings:
        original_get_settings.cache_clear()
        monkeypatch.setattr(config, "get_settings", lambda: settings)
        monkeypatch.setattr(
            "app.services.evaluation_service.get_settings",
            lambda: settings,
            raising=False,
        )
        monkeypatch.setattr(
            "app.services.refactor_service.get_settings",
            lambda: settings,
            raising=False,
        )
        return settings

    yield _apply
    original_get_settings.cache_clear()


@pytest.fixture(scope="session")
def dataset_root() -> Path:
    return PROJECT_ROOT / "dataset"


@pytest.fixture
def read_dataset_json(dataset_root):
    def _read(name: str):
        return json.loads((dataset_root / name).read_text(encoding="utf-8"))

    return _read


def make_scan(detected: list[str]) -> DetectionScanResult:
    """Builds a full 8-type scan with the given type names marked as detected."""
    heuristic_scan = HeuristicScan(
        signals={
            smell: SmellHeuristicSignal(smell_type=smell, possible=False, score=0.0)
            for smell in SmellType
        }
    )
    type_results = [
        TypeDetectionResult(
            type_name=name,
            detected=name in detected,
            evidencias=[],
            reasoning="fake",
        )
        for name in ALL_TYPE_NAMES
    ]
    return DetectionScanResult(heuristic_scan=heuristic_scan, type_results=type_results)


class FakeRefactorService:
    """Scripted stand-in: decisions keyed by sentinels in the source/solution."""

    async def detect(self, source_code: str) -> DetectionScanResult:
        if "BROKEN" in source_code:
            raise InvalidPythonCodeError("código não compila como Python: fake", line=1)
        detected: list[str] = []
        if "GOD" in source_code:
            detected += [SmellType.GOD_CLASS.value, PatternType.FACADE.value]
        if "SWITCH" in source_code:
            detected += [SmellType.COMPLEX_SWITCH.value, PatternType.STRATEGY.value]
        return make_scan(detected)

    async def run(self, request) -> RefactorResult:
        scan = make_scan([SmellType.GOD_CLASS.value, PatternType.FACADE.value])
        if request.file_name == "p1.py":
            proposal = RefactoringProposal(
                applied_pattern=PatternType.FACADE,
                refactored_code="def alpha():\n    return 1\n",
                architectural_explanation="fake",
                expected_benefits=["x"],
            )
            return RefactorResult(
                detection=scan,
                detected_problems=scan.detected_names(),
                target_smell=SmellType.GOD_CLASS,
                target_pattern=PatternType.FACADE,
                proposal=proposal,
                approved=True,
                iterations=1,
            )
        proposal = RefactoringProposal(
            applied_pattern=PatternType.STRATEGY,  # errado p/ o esperado Builder
            refactored_code="def gamma():\n    return 2\n",  # perde 'beta'
            architectural_explanation="fake",
            expected_benefits=["x"],
        )
        return RefactorResult(
            detection=scan,
            detected_problems=scan.detected_names(),
            target_smell=SmellType.GOD_CLASS,
            target_pattern=PatternType.FACADE,
            proposal=proposal,
            approved=False,
            iterations=3,
        )

    async def review(self, original: str, proposal: RefactoringProposal) -> ReflectionReview:
        approved = "APPROVE" in proposal.refactored_code
        return ReflectionReview(is_approved=approved, critique="fake")


@pytest.fixture
def dataset_dir(tmp_path):
    return tmp_path


@pytest.fixture
def write_text(dataset_dir):
    def _write(name: str, content: str):
        path = dataset_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def write_example(dataset_dir):
    """Writes an example file where the detector evaluation looks for it."""

    def _write(name: str, content: str):
        path = dataset_dir / "examples" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def write_json(dataset_dir):
    def _write(name: str, payload):
        path = dataset_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return _write


@pytest.fixture
def evaluation_service(dataset_dir, settings_factory, use_settings) -> EvaluationService:
    settings = settings_factory(dataset_dir=dataset_dir)
    use_settings(settings)
    return EvaluationService(FakeRefactorService())


@pytest.fixture
def broken_code():
    return "def broken(:"


@pytest.fixture
def long_params_code():
    return "def f(a, b, c, d, e):\n    return a+b+c+d+e\n"


@pytest.fixture
def god_class_code():
    body = "\n".join(f"    def m{i}(self): return {i}" for i in range(25))
    return f"class Big:\n{body}\n"


@pytest.fixture
def high_complexity_code():
    branches = "\n".join(
        f"    elif x == {i}: return {i}" for i in range(1, 15)
    )
    return f"def big(x):\n    if x == 0: return 0\n{branches}\n    else: return -1\n"


@pytest.fixture
def clean_code():
    return "def add(a, b):\n    return a + b\n"


@pytest.fixture
def diff_pair():
    return {
        "original": "def f(): return 1\n",
        "refactored": "def f(): return 2\n",
    }


@pytest.fixture
def identical_code():
    return "x = 1\n"


@pytest.fixture
def original_code():
    return """\
def calculate(x):
    return x


class Service:
    def run(self):
        return 1

    def _private(self):
        return 2
"""


@pytest.fixture
def refactored_without_service():
    return "def calculate(x):\n    return x\n"


@pytest.fixture
def refactored_with_syntax_error():
    return "def calculate(x)\n    return x\n"


@pytest.fixture
def valid_code():
    return "def f(): return 42\n"


@pytest.fixture
def invalid_code():
    return "def f(:\n"
