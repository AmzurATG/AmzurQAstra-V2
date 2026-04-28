"""Keyword-based domain classification over BRD + user story corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from features.functional.services.recommendation.domain_config import DomainRecord, DomainTestMappingFile


def _count_keyword(corpus_lower: str, kw: str) -> int:
    kw_stripped = kw.strip().lower()
    if not kw_stripped:
        return 0
    if " " in kw_stripped:
        # Phrase: count non-overlapping occurrences in lowercased corpus
        start = 0
        n = 0
        while True:
            i = corpus_lower.find(kw_stripped, start)
            if i < 0:
                break
            n += 1
            start = i + max(1, len(kw_stripped))
        return n
    pattern = r"\b" + re.escape(kw_stripped) + r"\b"
    return len(re.findall(pattern, corpus_lower))


@dataclass
class LocalClassificationResult:
    domain_id: str
    label: str
    confidence: float
    per_domain_scores: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, List[str]] = field(default_factory=dict)  # domain_id -> matched keyword strings
    score_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)  # domain_id -> {keyword: weighted}


def classify_domains_keyword(
    corpus: str,
    mapping: DomainTestMappingFile,
    *,
    general_domain_id: str = "general",
) -> LocalClassificationResult:
    """
    Score each domain (except pure fallback ordering) by weighted keyword hits.
    Confidence = (top1 - top2) / (top1 + 1e-6), capped to [0,1], with top2=0 giving high but not 1.0.
    """
    corpus_lower = corpus.lower()
    domains = [d for d in mapping.domains if d.id != general_domain_id]

    per_domain_scores: Dict[str, float] = {}
    evidence: Dict[str, List[str]] = {}
    breakdown: Dict[str, Dict[str, float]] = {}

    for d in domains:
        total = 0.0
        breakdown[d.id] = {}
        matched_terms: List[str] = []
        seen_kws: set[str] = set()
        for kw in d.keywords:
            kw_norm = kw.strip().lower()
            if not kw_norm or kw_norm in seen_kws:
                continue
            seen_kws.add(kw_norm)
            c = _count_keyword(corpus_lower, kw)
            if c <= 0:
                continue
            w = float(d.keyword_weights.get(kw, d.keyword_weights.get(kw_norm, 1.0)))
            contrib = c * w
            total += contrib
            breakdown[d.id][kw] = contrib
            if kw not in matched_terms:
                matched_terms.append(kw)
        per_domain_scores[d.id] = total
        evidence[d.id] = matched_terms

    # general domain gets score 0 for ranking purposes
    per_domain_scores[general_domain_id] = 0.0
    evidence.setdefault(general_domain_id, [])

    sorted_domains: List[Tuple[str, float]] = sorted(
        [(did, sc) for did, sc in per_domain_scores.items() if did != general_domain_id],
        key=lambda x: x[1],
        reverse=True,
    )
    top1 = sorted_domains[0][1] if sorted_domains else 0.0
    top2 = sorted_domains[1][1] if len(sorted_domains) > 1 else 0.0

    winner = general_domain_id
    winner_label = "General software"
    for d in mapping.domains:
        if d.id == general_domain_id:
            winner_label = d.label or winner_label
            break

    if sorted_domains and top1 > 0:
        winner = sorted_domains[0][0]
        rec = mapping_by_id(mapping, winner)
        winner_label = rec.label if rec else winner

    # Confidence from margin
    denom = top1 + 1e-6
    margin_conf = (top1 - top2) / denom if top1 > 0 else 0.0
    confidence = max(0.0, min(1.0, margin_conf))
    if top1 > 0 and top2 == 0:
        confidence = max(confidence, 0.75)

    return LocalClassificationResult(
        domain_id=winner,
        label=winner_label,
        confidence=float(confidence),
        per_domain_scores=per_domain_scores,
        evidence=evidence,
        score_breakdown=breakdown,
    )


def mapping_by_id(mapping: DomainTestMappingFile, domain_id: str) -> DomainRecord | None:
    for d in mapping.domains:
        if d.id == domain_id:
            return d
    return None


def strategies_for_domain(
    domain_id: str, mapping: DomainTestMappingFile, *, general_domain_id: str = "general"
) -> Tuple[List[dict], List[dict]]:
    """Return (standard_tests, recommended_tests) as plain dicts; fall back to general."""
    rec = mapping_by_id(mapping, domain_id)
    if not rec:
        rec = mapping_by_id(mapping, general_domain_id)
    if not rec:
        return [], []
    return [t.model_dump() for t in rec.standard_tests], [t.model_dump() for t in rec.recommended_tests]
