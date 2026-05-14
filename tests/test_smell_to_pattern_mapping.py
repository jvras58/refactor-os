import pytest

from app.tools.pattern_registry import (
    UnknownSmellError,
    list_supported_smells,
    normalize_smell,
    resolve_pattern_for_smell,
)


@pytest.mark.parametrize(
    ("raw_smell", "expected_normalized", "expected_pattern"),
    [
        (
            "Switch Statements",
            "Complex/Long Switch Statements",
            "Strategy Pattern",
        ),
        (
            "Complex/Long Switch Statements",
            "Complex/Long Switch Statements",
            "Strategy Pattern",
        ),
        (
            "Long Parameter List",
            "Long Parameter List",
            "Builder/Parameter Object",
        ),
        (
            "Data Clumps",
            "Long Parameter List",
            "Builder/Parameter Object",
        ),
        (
            "God Class",
            "God Class",
            "Facade/SRP",
        ),
        (
            "Large Class",
            "God Class",
            "Facade/SRP",
        ),
        (
            "Tight Coupling",
            "Tight Coupling",
            "Dependency Injection",
        ),
        (
            "Message Chains",
            "Tight Coupling",
            "Dependency Injection",
        ),
        (
            "Shotgun Surgery",
            "Tight Coupling",
            "Dependency Injection",
        ),
        (
            "Duplicated Code",
            "Duplicated Code",
            "Template Method",
        ),
        (
            "Duplicate Code",
            "Duplicated Code",
            "Template Method",
        ),
    ],
)
def test_resolve_pattern_for_smell(
    raw_smell,
    expected_normalized,
    expected_pattern,
):
    result = resolve_pattern_for_smell(raw_smell)

    assert normalize_smell(raw_smell) == expected_normalized
    assert result["normalized_smell"] == expected_normalized
    assert result["recommended_pattern"] == expected_pattern
    assert result["pattern_reference"]["name"] == expected_pattern
    assert result["pattern_reference"]["structure"]
    assert result["pattern_reference"]["rules"]


def test_smell_mapping_is_case_insensitive_and_trims_spaces():
    result = resolve_pattern_for_smell("   switch statements   ")

    assert result["normalized_smell"] == "Complex/Long Switch Statements"
    assert result["recommended_pattern"] == "Strategy Pattern"


def test_list_supported_smells_contains_dataset_compatible_labels():
    supported = list_supported_smells()

    assert "switch statements" in supported
    assert "data clumps" in supported
    assert "large class" in supported
    assert "message chains" in supported
    assert "duplicated code" in supported


def test_unknown_smell_raises_error():
    with pytest.raises(UnknownSmellError):
        resolve_pattern_for_smell("Singleton Abuse")
