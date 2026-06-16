"""Deterministic tests for the new multi-detector pipeline (no LLM, no DB).

Only phases 1 (validation), 2 (heuristic scan) and 4 (compilation) are testable
without an LLM/DB connection — they're ``@staticmethod``/plain classes, so we call
them directly without instantiating ``MultiDetectorService`` (whose ``__init__``
builds an Agno Agent + DB handle). Phase 3 (paired LLM calls) is exercised via a
manual smoke test against real examples, not in this automated suite.
"""
from __future__ import annotations

import pytest

from app.core.multi_detector_exceptions import InvalidPythonCodeError
from app.core.multi_detector_schemas import (
    DetectionScanResult,
    HeuristicScan,
    SmellHeuristicSignal,
    TypeDetectionResult,
)
from app.core.multi_detector_types import SmellType
from app.services.multi_detector_service import GroundTruthArrayCompiler, MultiDetectorService

# --------------------------------------------------------------- phase 1


def test_valid_python_passes_validation(clean_code):
    MultiDetectorService._validate_python(clean_code)  # não levanta


def test_invalid_python_raises_with_line(broken_code):
    with pytest.raises(InvalidPythonCodeError) as exc_info:
        MultiDetectorService._validate_python(broken_code)
    assert exc_info.value.line is not None


# --------------------------------------------------------------- phase 2


def test_heuristic_scan_always_has_all_4_smells(clean_code):
    scan = MultiDetectorService._run_heuristics(clean_code)
    assert set(scan.signals.keys()) == set(SmellType)


def test_heuristic_scan_clean_code_has_no_possible_smell(clean_code):
    scan = MultiDetectorService._run_heuristics(clean_code)
    assert all(not signal.possible for signal in scan.signals.values())
    assert all(signal.score == 0.0 for signal in scan.signals.values())


def test_heuristic_scan_detects_long_parameter_list(long_params_code):
    scan = MultiDetectorService._run_heuristics(long_params_code)
    signal = scan.signals[SmellType.LONG_PARAMETER]
    assert signal.possible
    assert signal.score > 0.0
    assert signal.line_start is not None
    # os outros 3 continuam presentes no dict, só que sem evidência
    others = [s for t, s in scan.signals.items() if t != SmellType.LONG_PARAMETER]
    assert len(others) == 3


def test_heuristic_scan_detects_god_class(god_class_code):
    scan = MultiDetectorService._run_heuristics(god_class_code)
    assert scan.signals[SmellType.GOD_CLASS].possible


def test_heuristic_scan_detects_complex_switch(high_complexity_code):
    scan = MultiDetectorService._run_heuristics(high_complexity_code)
    assert scan.signals[SmellType.COMPLEX_SWITCH].possible


# --------------------------------------------------------------- phase 4


def _fake_scan(detected_names: list[str]) -> DetectionScanResult:
    heuristic_scan = HeuristicScan(
        signals={
            smell: SmellHeuristicSignal(smell_type=smell, possible=False, score=0.0)
            for smell in SmellType
        }
    )
    all_names = [
        "Complex/Long Switch Statements", "Long Parameter List",
        "God Class", "Duplicated Code",
        "Strategy Pattern", "Builder", "Facade", "Template Method",
    ]
    type_results = [
        TypeDetectionResult(
            type_name=name,
            detected=name in detected_names,
            evidencias=[],
            reasoning="fake",
        )
        for name in all_names
    ]
    return DetectionScanResult(heuristic_scan=heuristic_scan, type_results=type_results)


def test_ground_truth_array_compiler_returns_only_detected():
    scan = _fake_scan(["Long Parameter List", "Builder"])
    result = GroundTruthArrayCompiler().compile(scan)
    assert result == ["Long Parameter List", "Builder"]


def test_ground_truth_array_compiler_empty_when_nothing_detected():
    scan = _fake_scan([])
    result = GroundTruthArrayCompiler().compile(scan)
    assert result == []


def test_service_compile_delegates_to_injected_compiler():
    class _StubCompiler:
        def compile(self, scan):
            return "stub"

    service = MultiDetectorService.__new__(MultiDetectorService)
    service._compiler = _StubCompiler()
    scan = _fake_scan([])
    assert service.compile(scan) == "stub"
