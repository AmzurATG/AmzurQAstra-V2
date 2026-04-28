"""Tests for keyword domain classifier and strategy resolution."""
from __future__ import annotations

import pytest

from features.functional.services.recommendation.domain_classifier import (
    classify_domains_keyword,
    strategies_for_domain,
    _count_keyword,
)
from features.functional.services.recommendation.domain_config import (
    DomainTestMappingFile,
    DomainRecord,
    PlaybookTestItem,
    reload_domain_test_mapping,
)


@pytest.fixture
def mini_mapping() -> DomainTestMappingFile:
    return DomainTestMappingFile(
        domains=[
            DomainRecord(
                id="general",
                label="General",
                keywords=[],
                standard_tests=[PlaybookTestItem(name="Smoke", category="Functional", priority="high", reason="baseline")],
                recommended_tests=[],
            ),
            DomainRecord(
                id="healthcare",
                label="Healthcare",
                keywords=["hipaa", "patient", "ehr"],
                keyword_weights={"hipaa": 3.0},
                standard_tests=[
                    PlaybookTestItem(name="PHI", category="Compliance", priority="high", reason="privacy")
                ],
                recommended_tests=[
                    PlaybookTestItem(name="FHIR", category="Interop", priority="medium", reason="exchange")
                ],
            ),
            DomainRecord(
                id="retail",
                label="Retail",
                keywords=["checkout", "sku"],
                standard_tests=[
                    PlaybookTestItem(name="Cart", category="Functional", priority="high", reason="revenue")
                ],
                recommended_tests=[],
            ),
        ]
    )


def test_count_keyword_word_boundary():
    text = "The patient record is for one patient only."
    assert _count_keyword(text.lower(), "patient") >= 1
    assert _count_keyword(text.lower(), "sku") == 0


def test_classify_healthcare_from_keywords(mini_mapping):
    corpus = "Our EHR stores patient data and must be HIPAA compliant for the hospital."
    result = classify_domains_keyword(corpus, mini_mapping, general_domain_id="general")
    assert result.domain_id == "healthcare"
    assert result.per_domain_scores["healthcare"] > result.per_domain_scores["retail"]
    assert "hipaa" in [k.lower() for k in result.evidence.get("healthcare", [])]


def test_classify_general_when_no_signals(mini_mapping):
    corpus = "Generic todo app with no domain hints."
    result = classify_domains_keyword(corpus, mini_mapping, general_domain_id="general")
    assert result.domain_id == "general"
    assert result.confidence == 0.0


def test_strategies_for_unknown_falls_back_general(mini_mapping):
    std, rec = strategies_for_domain("does-not-exist", mini_mapping, general_domain_id="general")
    assert any("Smoke" in s["name"] for s in std) or len(std) >= 1


def test_strategies_for_healthcare(mini_mapping):
    std, rec = strategies_for_domain("healthcare", mini_mapping, general_domain_id="general")
    assert any(s["name"] == "PHI" for s in std)
    assert any(s["name"] == "FHIR" for s in rec)


def test_load_packaged_yaml_mapping():
    m = reload_domain_test_mapping()
    ids = {d.id for d in m.domains}
    assert "general" in ids
    assert "healthcare" in ids
    std, _rec = strategies_for_domain("healthcare", m)
    assert len(std) >= 1
