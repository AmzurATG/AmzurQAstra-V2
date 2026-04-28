"""Readable PDF report for test recommendations (same tone/layout family as gap analysis reports)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

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


def build_test_recommendation_pdf(
    requirement_title: str,
    result: Dict[str, Any],
) -> bytes:
    """Render test recommendation playbook into a PDF (business-readable, no raw JSON)."""
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

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Testing recommendations report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    mc(
        5,
        "This report captures the recommended test focus areas for your requirement, "
        "based on your BRD text and the user stories included at run time.",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Document: {_ascii_safe(requirement_title, 200)}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Prepared: {generated}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Overview", ln=True)
    pdf.set_font("Helvetica", "", 10)
    summary = str(result.get("report_summary") or "").strip()
    if not summary:
        dom = result.get("domain_label") or result.get("domain_id") or "—"
        conf = result.get("confidence")
        src = result.get("source") or "—"
        pct = f"{float(conf) * 100:.0f}%" if isinstance(conf, (int, float)) else "—"
        summary = (
            f"Detected domain: {dom}. Confidence: {pct}. Classification source: {src}. "
            "See below for standard tests and additional recommendations."
        )
    mc(5, summary)
    pdf.ln(3)

    snap = result.get("input_snapshot") or {}
    if isinstance(snap, dict) and snap.get("user_stories_included"):
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "User stories included in this run", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        mc(
            4,
            "These are the project user stories that existed when the run was executed "
            "(same ordering as analysis: ascending id). Re-run after backlog changes.",
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)
        included = snap.get("user_stories_included")
        if isinstance(included, list):
            for i, row in enumerate(included[:120], 1):
                if not isinstance(row, dict):
                    continue
                key = row.get("external_key") or f"id:{row.get('id', '?')}"
                tit = _ascii_safe(str(row.get("title") or ""), 300)
                mc(4, f"{i}. [{key}] {tit}")
        total = snap.get("user_stories_total_in_project")
        if total is not None:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(90, 90, 90)
            mc(4, f"Total user stories in project at run time: {total}")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 10)
        pdf.ln(2)

    def write_table_section(heading: str, rows: List[Any]) -> None:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, heading, ln=True)
        pdf.set_font("Helvetica", "", 10)
        if not rows:
            mc(5, "No items.")
            pdf.ln(2)
            return
        for j, row in enumerate(rows[:80], 1):
            if not isinstance(row, dict):
                continue
            cat = _ascii_safe(str(row.get("category") or "—"), 120)
            name = _ascii_safe(str(row.get("name") or "—"), 300)
            pri = _ascii_safe(str(row.get("priority") or "—"), 40)
            why = _ascii_safe(str(row.get("reason") or "—"), 2000)
            pdf.set_font("Helvetica", "B", 11)
            mc(5, f"{j}. [{cat}] {name} — priority: {pri}")
            pdf.set_font("Helvetica", "", 10)
            mc(5, why)
            pdf.ln(1)
        pdf.ln(2)

    std = result.get("standard_tests") or []
    if isinstance(std, list):
        write_table_section("Standard tests (playbook)", std)

    recs = result.get("recommended_tests") or []
    if isinstance(recs, list):
        write_table_section("Additional recommendations", recs)

    warnings = result.get("warnings") or []
    if isinstance(warnings, list) and len(warnings) > 0:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Warnings", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for wline in warnings[:30]:
            mc(5, str(wline))

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return raw
