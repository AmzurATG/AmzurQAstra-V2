"""Load domain → test strategy mapping from YAML."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class PlaybookTestItem(BaseModel):
    category: str = ""
    name: str = ""
    priority: str = "medium"
    reason: str = ""


class DomainRecord(BaseModel):
    id: str
    label: str = ""
    keywords: List[str] = Field(default_factory=list)
    keyword_weights: Dict[str, float] = Field(default_factory=dict)
    standard_tests: List[PlaybookTestItem] = Field(default_factory=list)
    recommended_tests: List[PlaybookTestItem] = Field(default_factory=list)


class DomainTestMappingFile(BaseModel):
    domains: List[DomainRecord] = Field(default_factory=list)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "domain_test_mapping.yaml"


@lru_cache(maxsize=1)
def load_domain_test_mapping(path: Optional[str] = None) -> DomainTestMappingFile:
    """Load and validate domain mapping. Cached unless path overrides."""
    p = Path(path) if path else _default_config_path()
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("domain_test_mapping: root must be a mapping")
    return DomainTestMappingFile.model_validate(raw)


def mapping_by_domain_id(mapping: Optional[DomainTestMappingFile] = None) -> Dict[str, DomainRecord]:
    m = mapping or load_domain_test_mapping()
    return {d.id: d for d in m.domains}


def reload_domain_test_mapping(path: Optional[str] = None) -> DomainTestMappingFile:
    """Clear cache and reload (e.g. tests)."""
    load_domain_test_mapping.cache_clear()
    return load_domain_test_mapping(path)


def mapping_to_llm_domain_ids(mapping: DomainTestMappingFile) -> List[str]:
    return [d.id for d in mapping.domains]


def domains_catalog_for_prompt(mapping: DomainTestMappingFile) -> List[tuple[str, str]]:
    """(domain_id, label) pairs for LLM system prompt — order matches YAML."""
    return [(d.id, (d.label or "").strip() or d.id) for d in mapping.domains]
