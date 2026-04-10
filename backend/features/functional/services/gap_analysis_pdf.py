"""Build a readable PDF report from gap analysis (no raw JSON — suitable for non-technical readers)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict

from fpdf import FPDF
from fpdf.enums import Align, WrapMode, XPos, YPos


def _ascii_safe(s: str, max_len: int = 8000) -> str:
    if not s:
        return ""
    t = s[:max_len]
    return t.encode("ascii", "replace").decode("ascii")


def _soft_break_long_tokens(text: str, max_run: int = 48) -> str:
    if not text:
        return ""

    def repl(match: re.Match[str]) -> str:
        chunk = match.group(0)
        if len(chunk) <= max_run:
            return chunk
        return " ".join(chunk[i : i + max_run] for i in range(0, len(chunk), max_run))

    return re.sub(rf"\S{{{max_run + 1},}}", repl, text)


def _gap_type_plain(kind: str) -> str:
    """Turn internal gap types into short plain-English labels."""
    k = (kind or "").strip().lower()
    return {
        "inconsistency": "Conflict or mismatch",
        "missing_in_backlog": "Missing from current backlog",
        "coverage": "Coverage",
        "unknown": "Finding",
    }.get(k, kind.replace("_", " ").title() if kind else "Finding")


def build_gap_analysis_pdf(
    requirement_title: str,
    result: Dict[str, Any],
) -> bytes:
    """Render gap analysis into a PDF for business readers (no technical appendix)."""
    pdf = FPDF()
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    w = pdf.epw
    wm = WrapMode.WORD
    nx = XPos.LMARGIN
    ny = YPos.NEXT
    align = Align.L

    def mc(h: float, text: str) -> None:
        t = _soft_break_long_tokens(_ascii_safe(text))
        pdf.multi_cell(w, h, t, align=align, new_x=nx, new_y=ny, wrapmode=wm)

    generated = datetime.now(timezone.utc).strftime("%B %d, %Y · %H:%M UTC")

    # Title block
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Requirements coverage report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    mc(5, "This report compares your requirement document to the user stories in this project.")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Document: {_ascii_safe(requirement_title, 200)}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Prepared: {generated}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Divider
    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Overview", ln=True)
    pdf.set_font("Helvetica", "", 10)
    mc(5, str(result.get("summary", "") or "No summary was provided."))
    pdf.ln(3)

    cov = result.get("coverage_estimate_percent")
    if cov is not None:
        pdf.set_fill_color(245, 247, 250)
        pdf.set_font("Helvetica", "B", 11)
        box_h = 10
        pdf.cell(0, box_h, f"  Approximate alignment with backlog: {cov}%", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(90, 90, 90)
        mc(
            4,
            "This is an estimate of how much of the requirement themes are reflected in existing user stories — not a formal test metric.",
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    gaps = result.get("gaps") or []
    if gaps:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Findings", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for i, g in enumerate(gaps[:50], 1):
            if not isinstance(g, dict):
                g = {}
            kind = _gap_type_plain(str(g.get("type", "") or "?"))
            detail = _ascii_safe(str(g.get("detail", "")), 4000)
            line = f"{i}. {kind} — {detail}"
            if g.get("related_story_key"):
                line += f"\n   Related work items: {g.get('related_story_key')}"
            mc(5, line)
            pdf.ln(1)
        pdf.ln(2)

    suggested = result.get("suggested_user_stories") or []
    if suggested:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Suggested additions to your backlog", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        mc(
            4,
            "The following ideas are generated suggestions. You can add them as user stories from the application when ready.",
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        for i, s in enumerate(suggested[:20], 1):
            if not isinstance(s, dict):
                s = {}
            pdf.set_font("Helvetica", "B", 11)
            mc(5, f"{i}. {_ascii_safe(str(s.get('title', '')), 200)}")
            pdf.set_font("Helvetica", "", 10)
            if s.get("description"):
                mc(5, str(s.get("description", ""))[:2000])
            if s.get("acceptance_criteria"):
                pdf.set_font("Helvetica", "B", 9)
                mc(4, "Acceptance criteria")
                pdf.set_font("Helvetica", "", 9)
                mc(4, _ascii_safe(str(s.get("acceptance_criteria")), 2000))
            if s.get("rationale"):
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(70, 70, 70)
                mc(
                    4,
                    "Why this matters: " + _ascii_safe(str(s.get("rationale")), 800),
                )
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 10)
            pdf.ln(3)

    notes = result.get("notes")
    if notes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Additional notes", ln=True)
        pdf.set_font("Helvetica", "", 10)
        mc(5, str(notes))

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return raw
