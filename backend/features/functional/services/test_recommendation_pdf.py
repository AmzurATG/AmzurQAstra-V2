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
    std = result.get("standard_tests") or []
    if not isinstance(std, list):
        std = []
    recs = result.get("recommended_tests") or []
    if not isinstance(recs, list):
        recs = []

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

    def write_playbook_section(heading: str, rows: List[Any]) -> None:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 10, heading, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        if not rows:
            mc(5, "No specific items identified for this section.")
            pdf.ln(2)
            return
        
        for j, row in enumerate(rows[:80], 1):
            if not isinstance(row, dict):
                continue
            cat = _ascii_safe(str(row.get("category") or "-"), 120)
            name = _ascii_safe(str(row.get("name") or "-"), 300)
            pri = _ascii_safe(str(row.get("priority") or "-"), 40)
            why = _ascii_safe(str(row.get("reason") or "-"), 2000)
            
            # Item Header
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(0, 8, f" {j}. [{cat}] {name}", ln=True, fill=True)
            
            # Priority & Necessity
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(25, 6, "Priority:", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, pri.capitalize(), ln=True)
            
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(25, 6, "Necessity:", ln=False)
            pdf.set_font("Helvetica", "", 10)
            mc(6, why)
            
            # Context/Guidance
            dg = str(row.get("detailed_guidance") or "").strip()
            if dg:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(25, 6, "Context:", ln=False)
                pdf.set_font("Helvetica", "I", 10)
                mc(6, dg)
                pdf.set_text_color(0, 0, 0)
            
            pdf.ln(2)
        pdf.ln(2)

    # Variables for header and summary
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y")
    dom = str(result.get("domain_label") or result.get("domain_id") or "your product").strip()

    # Document Header
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 15, "Test Strategy Recommendations", ln=True, align='C')
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Requirement: {_ascii_safe(requirement_title, 200)}", ln=True, align='C')
    pdf.cell(0, 6, f"Date: {generated}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(10)

    # 1. Executive Summary
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(60, 60, 60)
    
    dr = result.get("detailed_report")
    if isinstance(dr, dict) and dr.get("summary_paragraph"):
        summary_p = str(dr.get("summary_paragraph")).strip()
        mc(6, f'"{summary_p}"')
    else:
        mc(6, f"This report provides a multi-layered testing strategy for {dom}. "
              "Our recommendations focus on ensuring functional integrity, security compliance, and "
              "integration stability based on the provided requirements and current backlog.")
    pdf.ln(8)

    # 2. Recommended Test Focus Areas
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "2. Recommended Test Focus Areas", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    mc(5, "The following areas have been identified as critical for maintaining high quality and mitigating risks. "
          "Each recommendation includes a justification for its necessity and tailored context where applicable.")
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    write_playbook_section("2.1 Primary Baseline Tests", std)
    write_playbook_section("2.2 Domain-Specific Recommendations", recs)

    # 3. Context and Analysis (New Page)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "3. Context and Analysis", ln=True)
    pdf.ln(4)

    # 3.1 Product Intent
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "3.1 Product Intent", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    intent = str(result.get("intent_summary") or "").strip()
    if intent:
        mc(5, intent)
    else:
        mc(5, "Based on the requirements, the product intent centers on delivering core functional value within its domain.")
    pdf.ln(6)

    # 3.2 Backlog Coverage
    gap_snap = result.get("gap_analysis_snapshot")
    if isinstance(gap_snap, dict) and gap_snap:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 8, "3.2 Backlog Coverage (Gap Analysis)", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        gs = str(gap_snap.get("summary") or "").strip()
        if gs:
            mc(5, gs)
        cov = gap_snap.get("coverage_estimate_percent")
        if cov is not None:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Estimated Backlog Coverage: {cov}%", ln=True)
        pdf.ln(6)

    # 3.3 Methodology
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 8, "3.3 Methodology Note", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    
    summary_line = str(result.get("report_summary") or "").strip()
    if summary_line:
        mc(4, summary_line)
    
    merge_note = str(result.get("playbook_merge_note") or "").strip().replace("*", "")
    if merge_note:
        mc(4, merge_note)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # Warnings
    warnings = result.get("warnings") or []
    if isinstance(warnings, list) and len(warnings) > 0:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(180, 0, 0)
        pdf.cell(0, 10, "Warnings and Observations", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        for wline in warnings[:30]:
            mc(5, str(wline))

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return raw
