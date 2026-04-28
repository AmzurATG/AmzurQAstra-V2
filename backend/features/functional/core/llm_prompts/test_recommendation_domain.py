"""LLM fallback: classify business domain from corpus text."""
from __future__ import annotations


def build_test_recommendation_domain_system_message(allowed_domain_ids: list[str]) -> str:
    allowed = ", ".join(f'"{x}"' for x in allowed_domain_ids)
    return f"""You classify the business domain of a software product from a draft requirements document and user story titles/descriptions.
Pick exactly one domain_id from this list: [{allowed}].

Respond with a single JSON object only (no markdown, no code fences):
{{"domain_id": "<one of the allowed ids>", "confidence": <number from 0 to 1>, "rationale": "<short string>"}}

Rules:
- Prefer the most specific domain when evidence supports it; use \"general\" only when none fit well.
- confidence reflects how sure you are (0.9+ when evidence is strong).
"""
