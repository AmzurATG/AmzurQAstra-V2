"""Formal PDF report for Build Integrity Check runs (fpdf2)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from fpdf import FPDF
from fpdf.enums import Align, WrapMode, XPos, YPos


def _ascii_safe(s: str, max_len: int = 12000) -> str:
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


def build_integrity_check_pdf(
    *,
    run_id: str,
    app_url: str,
    db_status: str,
    overall_status: Optional[str],
    app_reachable: Optional[bool],
    steps_total: int,
    steps_passed: int,
    steps_failed: int,
    summary: Optional[str],
    error_message: Optional[str],
    steps_data: Optional[List[Any]],
    screenshots: Optional[List[Any]],
    duration_ms: Optional[int],
    completed_at: Optional[datetime],
) -> bytes:
    """Render a BIC run into a PDF suitable for email attachment."""
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

    now_line = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if completed_at is not None:
        if completed_at.tzinfo is None:
            dt_utc = completed_at.replace(tzinfo=timezone.utc)
        else:
            dt_utc = completed_at.astimezone(timezone.utc)
        finished_line = dt_utc.strftime("%Y-%m-%d %H:%M UTC")
    else:
        finished_line = "—"

    outcome = (overall_status or db_status or "unknown").strip().lower()
    outcome_title = {
        "passed": "Outcome: passed",
        "failed": "Outcome: failed",
        "error": "Outcome: error",
        "completed": "Outcome: see summary",
    }.get(outcome, f"Outcome: {outcome}")

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Build integrity check report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    mc(
        5,
        "Automated verification that your application URL is reachable and loads after login.",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Run id: {_ascii_safe(run_id, 128)}", ln=True)
    pdf.cell(0, 5, f"Application URL: {_ascii_safe(app_url, 500)}", ln=True)
    pdf.cell(0, 5, f"Run status: {_ascii_safe(db_status, 40)}", ln=True)
    pdf.cell(0, 5, f"{_ascii_safe(outcome_title, 80)}", ln=True)
    if app_reachable is not None:
        pdf.cell(
            0,
            5,
            f"Application reachable: {'yes' if app_reachable else 'no'}",
            ln=True,
        )
    dur = duration_ms
    if dur is not None:
        d_txt = f"{dur} ms" if dur < 1000 else f"{dur / 1000:.1f} s"
        pdf.cell(0, 5, f"Duration: {d_txt}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Report prepared: {now_line}", ln=True)
    pdf.cell(0, 5, f"Run completed: {finished_line}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Step summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Total steps: {int(steps_total or 0)}", ln=True)
    pdf.cell(0, 5, f"Passed: {int(steps_passed or 0)}", ln=True)
    pdf.cell(0, 5, f"Failed: {int(steps_failed or 0)}", ln=True)
    pdf.ln(3)

    if summary and str(summary).strip():
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Summary", ln=True)
        pdf.set_font("Helvetica", "", 10)
        mc(5, str(summary))
        pdf.ln(2)

    if error_message and str(error_message).strip():
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Error details", ln=True)
        pdf.set_font("Helvetica", "", 10)
        mc(5, str(error_message))
        pdf.ln(2)

    raw_steps = list(steps_data or [])
    if raw_steps:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Recorded steps", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for i, row in enumerate(raw_steps[:80], start=1):
            if isinstance(row, dict):
                sn = row.get("step_number", i)
                desc = row.get("description") or row.get("current_step") or ""
                shot = row.get("screenshot_path") or ""
            else:
                sn, desc, shot = i, str(row), ""
            line = f"{sn}. {_ascii_safe(str(desc), 2000)}"
            if shot:
                line += f"  [{_ascii_safe(str(shot), 300)}]"
            mc(4, line)
        if len(raw_steps) > 80:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, f"(… {len(raw_steps) - 80} more steps not shown)", ln=True)
        pdf.ln(2)

    shots = list(screenshots or [])
    if shots:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, f"Screenshots ({len(shots)} files)", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for p in shots[:40]:
            mc(4, f"- {_ascii_safe(str(p), 500)}")
        if len(shots) > 40:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, f"(… {len(shots) - 40} more paths not listed)", ln=True)

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return raw
