from app.tools.pattern_registry import DESIGN_PATTERNS, lookup_pattern


def test_lookup_pattern_canonical_name():
    out = lookup_pattern("Strategy Pattern")
    assert out["name"] == "Strategy Pattern"
    assert out["applies_to"] == "Complex/Long Switch Statements"
    assert out["structure"]


def test_lookup_pattern_alias_resolution():
    assert lookup_pattern("di")["name"] == "Dependency Injection"
    assert lookup_pattern("template method")["name"] == "Template Method"
    assert lookup_pattern("FACADE")["name"] == "Facade/SRP"


def test_lookup_pattern_unsupported():
    out = lookup_pattern("Singleton")
    assert "error" in out
    assert "supported" in out


def test_registry_covers_five_patterns():
    assert set(DESIGN_PATTERNS.keys()) == {
        "Strategy Pattern",
        "Builder/Parameter Object",
        "Facade/SRP",
        "Dependency Injection",
        "Template Method",
    }
