"""Formal PDF report for orchestrated test runs (fpdf2), with embedded screenshots."""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fpdf import FPDF
from fpdf.enums import Align, WrapMode, XPos, YPos

from config import settings
from common.utils.logger import logger
from features.functional.core.case_budget import format_duration_ms


def _ascii_safe(s: Any, max_len: int = 8000) -> str:
    if s is None:
        return ""
    t = str(s)[:max_len]
    return t.encode("ascii", "replace").decode("ascii")


def _soft_break(text: str, max_run: int = 48) -> str:
    if not text:
        return ""

    def repl(m: re.Match[str]) -> str:
        chunk = m.group(0)
        if len(chunk) <= max_run:
            return chunk
        return " ".join(chunk[i : i + max_run] for i in range(0, len(chunk), max_run))

    return re.sub(rf"\S{{{max_run + 1},}}", repl, text)


def _screenshot_bytes(path: Optional[str]) -> Optional[bytes]:
    if not path:
        return None
    try:
        fname = Path(str(path)).name
        fp = Path(settings.SCREENSHOTS_DIR) / fname
        if fp.is_file():
            return fp.read_bytes()
    except Exception:
        return None
    return None


def build_test_run_pdf(report: Dict[str, Any]) -> bytes:
    """Render the structured report (from build_report_data) into a PDF."""
    pdf = FPDF()
    pdf.set_left_margin(16)
    pdf.set_right_margin(16)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    w = pdf.epw

    def mc(h: float, text: str, size: int = 10, style: str = "") -> None:
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(
            w, h, _soft_break(_ascii_safe(text)),
            align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT, wrapmode=WrapMode.WORD,
        )

    totals = report.get("totals", {})
    now_line = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, f"Test Run Report #{report.get('run_number') or report.get('run_id')}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    mc(5, f"Application: {report.get('app_url') or '-'}")
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, f"Status: {report.get('status')}", ln=True)
    pdf.cell(
        0, 5,
        f"Total: {totals.get('total', 0)}   Passed: {totals.get('passed', 0)}   "
        f"Failed: {totals.get('failed', 0)}   Blocked: {totals.get('blocked', 0)}   "
        f"Skipped: {totals.get('skipped', 0)}   "
        f"Success: {totals.get('success_rate', 0)}%",
        ln=True,
    )
    run_dur = totals.get("duration_display") or format_duration_ms(totals.get("duration_ms"))
    sum_dur = totals.get("sum_case_duration_display") or format_duration_ms(
        totals.get("sum_case_duration_ms")
    )
    pdf.cell(0, 5, f"Run wall time: {run_dur}   ·   Sum of case times: {sum_dur}", ln=True)
    if report.get("started_at") or report.get("completed_at"):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(
            0, 5,
            f"Started: {report.get('started_at') or '-'}   Completed: {report.get('completed_at') or '-'}",
            ln=True,
        )
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"AI adaptations recorded: {totals.get('adaptations', 0)}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"Prepared: {now_line}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    def _render_case(case: Dict[str, Any], embed_full: bool) -> None:
        status = case.get("status", "")
        infra = bool(case.get("infra_error"))
        if status == "passed":
            mark = "PASS"
        elif infra or status == "error":
            mark = "BLOCKED"
        else:
            mark = status.upper()
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(
            w, 6, _soft_break(_ascii_safe(
                f"[{mark}] {case.get('title')} (case #{case.get('test_case_id')})"
            )),
            align=Align.L, new_x=XPos.LMARGIN, new_y=YPos.NEXT, wrapmode=WrapMode.WORD,
        )
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(110, 110, 110)
        dur_txt = case.get("duration_display") or format_duration_ms(case.get("duration_ms") or 0)
        pdf.cell(
            0, 5,
            f"Steps {case.get('steps_passed', 0)}/{case.get('steps_total', 0)} passed"
            f"  ·  Duration: {dur_txt}"
            + (f"  ·  {case.get('adaptation_count')} AI adaptation(s)" if case.get("adaptation_count") else ""),
            ln=True,
        )
        pdf.set_text_color(0, 0, 0)
        msg = case.get("user_message") or case.get("error_message")
        if msg:
            mc(4, f"{'Note' if infra else 'Error'}: {msg}", size=9, style="I")

        for s in case.get("steps", [])[:60]:
            sn = s.get("step_number", "?")
            st = s.get("status", "")
            desc = s.get("description") or ""
            exp = s.get("expected_result") or ""
            act = s.get("actual_result") or ""
            adapt = s.get("adaptation")
            mc(4, f"  {sn}. [{st}] {desc}", size=9, style="B" if st == "failed" else "")
            if exp:
                mc(4, f"      Expected: {exp}", size=8)
            if act:
                mc(4, f"      Actual: {act}", size=8)
            if adapt:
                pdf.set_text_color(120, 60, 160)
                mc(4, f"      AI adaptation: {adapt}", size=8, style="I")
                pdf.set_text_color(0, 0, 0)

        img = _screenshot_bytes(case.get("screenshot_path"))
        if img:
            try:
                width = w if embed_full else w * 0.55
                pdf.image(io.BytesIO(img), w=width)
                pdf.ln(1)
            except Exception as exc:
                logger.warning("[TestRunPDF] embed screenshot failed: %s", exc)
        pdf.ln(2)

    failed_cases = report.get("failed_cases", [])
    if failed_cases:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, f"Failures ({len(failed_cases)})", ln=True)
        pdf.ln(1)
        for c in failed_cases:
            _render_case(c, embed_full=True)

    blocked_cases = report.get("blocked_cases", [])
    if blocked_cases:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, f"Blocked / infrastructure ({len(blocked_cases)})", ln=True)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 5, "Not recorded as application test failures.", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)
        for c in blocked_cases:
            _render_case(c, embed_full=True)

    for g in report.get("groups", []):
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(
            0, 8,
            _ascii_safe(f"Group: {g.get('title')}  ({g.get('passed', 0)}/{g.get('total', 0)} passed)"),
            ln=True,
        )
        pdf.ln(1)
        for c in g.get("cases", []):
            _render_case(c, embed_full=(c.get("status") != "passed"))

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return raw
