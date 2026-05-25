"""Shared pytest fixtures for the test suite."""

import json

import pytest

from app.core import config
from app.core.schemas import (
    BadSmellType,
    DesignPatternType,
    RefactoringProposal,
    RefactorResult,
    ReflectionReview,
    SmellDetection,
)
from app.services.evaluation_service import EvaluationService


@pytest.fixture
def settings() -> config.Settings:
    return config.Settings(_env_file=None)


@pytest.fixture
def settings_factory(tmp_path):
    def _factory(**overrides) -> config.Settings:
        dataset_dir = overrides.pop("dataset_dir", tmp_path / "dataset")
        patterns_dir = overrides.pop("patterns_dir", tmp_path / "patterns")
        dataset_dir.mkdir(parents=True, exist_ok=True)
        patterns_dir.mkdir(parents=True, exist_ok=True)
        return config.Settings(
            _env_file=None,
            dataset_dir=dataset_dir,
            patterns_dir=patterns_dir,
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
        monkeypatch.setattr(
            "app.services.knowledge_service.get_settings",
            lambda: settings,
            raising=False,
        )
        return settings

    yield _apply
    original_get_settings.cache_clear()


class FakeRefactorService:
    """Scripted stand-in: decisions keyed by sentinels in the source/solution."""

    async def detect(self, source_code: str) -> SmellDetection:
        if "GOD" in source_code:
            return SmellDetection(
                has_smell=True, smell_type=BadSmellType.GOD_CLASS, reasoning="fake"
            )
        return SmellDetection(has_smell=False, smell_type=BadSmellType.NO_SMELL, reasoning="fake")

    async def run(self, request) -> RefactorResult:
        detection = SmellDetection(has_smell=True, smell_type=BadSmellType.GOD_CLASS, reasoning="fake")
        if request.file_name == "p1.py":
            proposal = RefactoringProposal(
                applied_pattern=DesignPatternType.FACADE_SRP,
                refactored_code="def alpha():\n    return 1\n",
                architectural_explanation="fake",
                expected_benefits=["x"],
            )
            return RefactorResult(detection=detection, proposal=proposal, approved=True, iterations=1)
        proposal = RefactoringProposal(
            applied_pattern=DesignPatternType.STRATEGY,  # errado p/ Long Parameter
            refactored_code="def gamma():\n    return 2\n",  # perde 'beta'
            architectural_explanation="fake",
            expected_benefits=["x"],
        )
        return RefactorResult(detection=detection, proposal=proposal, approved=False, iterations=3)

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
