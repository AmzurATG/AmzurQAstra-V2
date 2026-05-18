"""
Extract structured summary content for client-facing report emails (body + PDF attachment).

Kept separate from SMTP transport so API layers can unit-test extraction logic easily.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAX_SUMMARY_CHARS = 4000
_MAX_HIGHLIGHT_ITEMS = 7
_MAX_GAP_DETAIL_CHARS = 280
_MAX_STRATEGY_REASON_CHARS = 200
_MAX_IC_SUMMARY_CHARS = 4500


@dataclass(frozen=True)
class RichReportEmailParts:
    """Optional sections appended to formal report emails."""

    executive_summary: str | None = None
    """One or more paragraphs suitable for email (plain text; HTML will escape)."""

    highlights: tuple[str, ...] = ()
    """Short bullet lines (already plain text)."""

    metrics: tuple[str, ...] = ()
    """Short factual lines, e.g. coverage % or step counts."""


def _truncate(s: str, max_len: int) -> str:
    t = (s or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _gap_type_plain(kind: str) -> str:
    k = (kind or "").strip().lower()
    return {
        "inconsistency": "Conflict or mismatch",
        "missing_in_backlog": "Missing from backlog",
        "coverage": "Coverage",
        "unknown": "Finding",
    }.get(k, (kind or "Finding").replace("_", " ").title())


def _priority_rank(p: str | None) -> int:
    x = (p or "").lower().strip()
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x, 4)


def rich_parts_for_gap_analysis(result: dict[str, Any] | None) -> RichReportEmailParts:
    if not result or not isinstance(result, dict):
        return RichReportEmailParts()

    summary = _truncate(str(result.get("summary") or "").strip(), _MAX_SUMMARY_CHARS)

    metrics: list[str] = []
    cov = result.get("coverage_estimate_percent")
    if cov is not None:
        try:
            metrics.append(f"Approximate alignment with current backlog: {int(cov)}%")
        except (TypeError, ValueError):
            metrics.append(f"Approximate alignment with current backlog: {cov}")

    highlights: list[str] = []
    gaps = result.get("gaps") or []
    if isinstance(gaps, list):
        for g in gaps:
            if len(highlights) >= _MAX_HIGHLIGHT_ITEMS:
                break
            if not isinstance(g, dict):
                continue
            kind = _gap_type_plain(str(g.get("type", "") or ""))
            detail = _truncate(str(g.get("detail", "") or "").strip(), _MAX_GAP_DETAIL_CHARS)
            if not detail:
                continue
            line = f"{kind}: {detail}"
            if g.get("related_story_key"):
                line += f" (related: {g.get('related_story_key')})"
            highlights.append(line)

    return RichReportEmailParts(
        executive_summary=summary or None,
        highlights=tuple(highlights),
        metrics=tuple(metrics),
    )


def rich_parts_for_test_recommendations(result: dict[str, Any] | None) -> RichReportEmailParts:
    if not result or not isinstance(result, dict):
        return RichReportEmailParts()

    dr = result.get("detailed_report")
    summary = ""
    if isinstance(dr, dict):
        summary = str(dr.get("summary_paragraph") or "").strip()
    if not summary:
        summary = str(result.get("intent_summary") or "").strip()

    metrics: list[str] = []
    dom = str(result.get("domain_label") or result.get("domain_id") or "").strip()
    if dom:
        metrics.append(f"Product / domain context: {dom}")

    rows: list[dict[str, Any]] = []
    for key in ("standard_tests", "recommended_tests"):
        chunk = result.get(key) or []
        if isinstance(chunk, list):
            for item in chunk:
                if isinstance(item, dict):
                    rows.append(item)

    rows.sort(key=lambda r: _priority_rank(str(r.get("priority"))))

    highlights: list[str] = []
    for row in rows:
        cat = str(row.get("category") or "").strip()
        name = str(row.get("name") or "").strip()
        pri = str(row.get("priority") or "").strip()
        why = _truncate(str(row.get("reason") or "").strip(), _MAX_STRATEGY_REASON_CHARS)
        if not name and not cat:
            continue
        label = f"[{cat}] {name}" if cat else name
        if pri:
            label = f"{label} ({pri})"
        if why:
            label = f"{label} — {why}"
        highlights.append(label)
        if len(highlights) >= _MAX_HIGHLIGHT_ITEMS:
            break

    return RichReportEmailParts(
        executive_summary=_truncate(summary, _MAX_SUMMARY_CHARS) if summary else None,
        highlights=tuple(highlights),
        metrics=tuple(metrics),
    )


def rich_parts_for_integrity_check(
    *,
    summary: str | None,
    overall_status: str | None,
    steps_total: int | None,
    steps_passed: int | None,
    steps_failed: int | None,
) -> RichReportEmailParts:
    summ_raw = str(summary or "").strip()
    summ = _truncate(summ_raw, _MAX_IC_SUMMARY_CHARS) if summ_raw else None

    metrics: list[str] = []
    status = (overall_status or "").strip().lower()
    if status:
        pretty = {
            "passed": "Overall outcome: Passed",
            "failed": "Overall outcome: Failed",
            "error": "Overall outcome: Completed with errors",
        }.get(status, f"Overall outcome: {status.title()}")
        metrics.append(pretty)

    if steps_total is not None and steps_total > 0:
        p = steps_passed if steps_passed is not None else 0
        f = steps_failed if steps_failed is not None else 0
        metrics.append(f"Recorded steps: {p} passed, {f} failed (of {steps_total} total)")

    return RichReportEmailParts(
        executive_summary=summ,
        highlights=(),
        metrics=tuple(metrics),
    )
