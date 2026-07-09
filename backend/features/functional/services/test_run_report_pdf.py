"""
Comprehensive PDF report builder for functional test runs.

Sections:
  1. Cover page  — project, run meta, summary KPIs
  2. Executive summary — pass-rate, story/requirement coverage overview
  3. Requirements (BRDs) — if any test cases are linked
  4. User stories — grouped with per-case result tables
  5. Execution details — every test case: steps + screenshots
  6. Failures digest — all failed/error cases consolidated
  7. Screenshot appendix — full index of captured evidence files
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fpdf import FPDF
from fpdf.enums import Align, WrapMode, XPos, YPos


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _asc(s: Any, max_len: int = 8000) -> str:
    """
    Sanitise a value for use as text in an fpdf2 core-font (Helvetica/Latin-1) cell.
    Uses Latin-1 (ISO 8859-1) encoding so accented letters survive while
    Unicode-only characters (em dash, checkmarks, etc.) are replaced with '?'.
    """
    if not s:
        return ""
    # Pre-substitute common Unicode punctuation with safe ASCII equivalents
    t = (
        str(s)[:max_len]
        .replace("\u2014", " - ")   # em dash  —
        .replace("\u2013", " - ")   # en dash  –
        .replace("\u2022", "*")     # bullet   •
        .replace("\u2019", "'")     # right single quote  '
        .replace("\u2018", "'")     # left single quote   '
        .replace("\u201c", '"')     # left double quote   "
        .replace("\u201d", '"')     # right double quote  "
        .replace("\u2026", "...")   # ellipsis …
        .replace("\u2713", "[OK]")  # checkmark ✓
        .replace("\u2715", "[X]")   # cross mark ✗
        .replace("\u2717", "[X]")   # ballot x  ✗
    )
    return t.encode("latin-1", "replace").decode("latin-1")


def _wrap(text: str, max_run: int = 50) -> str:
    if not text:
        return ""

    def repl(m: re.Match[str]) -> str:
        chunk = m.group(0)
        if len(chunk) <= max_run:
            return chunk
        return " ".join(chunk[i: i + max_run] for i in range(0, len(chunk), max_run))

    return re.sub(rf"\S{{{max_run + 1},}}", repl, text)


def _fmt_ms(ms: Optional[int]) -> str:
    if ms is None:
        return "-"
    if ms < 1000:
        return f"{ms} ms"
    s = ms / 1000
    if s < 60:
        return f"{s:.1f} s"
    m, sec = divmod(int(s), 60)
    if m < 60:
        return f"{m}m {sec:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {sec:02d}s"


def _fmt_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Show both UTC and a local-friendly clock for stakeholders.
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _wall_clock(started: Optional[datetime], completed: Optional[datetime]) -> str:
    if not started or not completed:
        return "-"
    a = started if started.tzinfo else started.replace(tzinfo=timezone.utc)
    b = completed if completed.tzinfo else completed.replace(tzinfo=timezone.utc)
    ms = int((b - a).total_seconds() * 1000)
    return _fmt_ms(ms) if ms >= 0 else "-"


def _status_color(status: str) -> tuple[int, int, int]:
    s = (status or "").lower()
    if s == "passed":
        return (22, 163, 74)     # green-600
    if s in ("failed", "error"):
        return (220, 38, 38)     # red-600
    if s == "skipped":
        return (107, 114, 128)   # gray-500
    if s == "cancelled":
        return (180, 83, 9)      # amber-700
    return (99, 102, 241)        # indigo-500


def _pass_rate_color(rate: int) -> tuple[int, int, int]:
    if rate >= 80:
        return (22, 163, 74)
    if rate >= 50:
        return (202, 138, 4)  # amber
    return (220, 38, 38)


def _resolve_screenshot_path(raw_path: str, screenshots_dir: str) -> Optional[str]:
    """Convert /screenshots/file.png or an absolute path to a readable file path."""
    if not raw_path:
        return None
    p = Path(raw_path)
    if p.is_absolute() and p.exists():
        return str(p)
    # Strip leading /screenshots/ prefix
    fname = p.name
    candidate = Path(screenshots_dir) / fname
    if candidate.exists():
        return str(candidate)
    return None


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

class _ReportPDF(FPDF):
    """Custom FPDF with branded header/footer."""

    def __init__(self, project_name: str, run_label: str):
        super().__init__()
        self._proj = _asc(project_name, 80)
        self._run_label = _asc(run_label, 80)

    def header(self):
        if self.page == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, _asc(f"QAstra - {self._proj} | {self._run_label}"), align="L")
        self.ln(4)
        self.set_draw_color(230, 230, 230)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(60, 6, "QAstra Functional Testing", align="L")
        self.cell(0, 6, f"Page {self.page}", align="C")
        self.set_text_color(0, 0, 0)


def build_test_run_report_pdf(
    *,
    project_name: str,
    run_number: int,
    run_name: Optional[str],
    run_status: str,
    run_browser: Optional[str],
    run_started_at: Optional[datetime],
    run_completed_at: Optional[datetime],
    total_tests: int,
    passed_tests: int,
    failed_tests: int,
    skipped_tests: int,
    results: List[Dict[str, Any]],
    requirements: Dict[int, Dict[str, Any]],
    user_stories: Dict[int, Dict[str, Any]],
    screenshots_dir: str,
    report_format: str = "short",
) -> bytes:
    """
    Build a PDF for a functional test run.

    report_format:
      ``short`` (default) — cover, results index, failures digest + evidence.
        Suitable for demos / email (tens of pages, not thousands).
      ``long`` — full per-case step detail, agent logs, and screenshot appendix.
    """
    fmt = (report_format or "short").strip().lower()
    if fmt not in ("short", "long"):
        fmt = "short"
    run_label = f"Run #{run_number} ({fmt})"
    pdf = _ReportPDF(project_name=project_name, run_label=run_label)
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    pdf.set_auto_page_break(auto=True, margin=20)

    w = pdf.epw
    wm = WrapMode.WORD
    nx = XPos.LMARGIN
    ny = YPos.NEXT
    align_l = Align.L

    def mc(h: float, text: str, *, color: tuple = (0, 0, 0)) -> None:
        if h <= 0:
            h = 5
        pdf.set_text_color(*color)
        pdf.multi_cell(w, h, _wrap(_asc(text)), align=align_l, new_x=nx, new_y=ny, wrapmode=wm)
        pdf.set_text_color(0, 0, 0)

    def fill_band(
        text: str,
        *,
        height: float = 7,
        fill: tuple[int, int, int] = (248, 250, 252),
        color: tuple[int, int, int] = (0, 0, 0),
        font_size: int = 9,
        bold: bool = True,
    ) -> None:
        """Full-width coloured band that always advances the cursor downward."""
        pdf.set_fill_color(*fill)
        pdf.set_font("Helvetica", "B" if bold else "", font_size)
        pdf.set_text_color(*color)
        pdf.cell(0, height, _asc(text), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    def divider() -> None:
        pdf.set_draw_color(220, 220, 220)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(5)

    def section_title(title: str) -> None:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(248, 250, 252)
        pdf.cell(0, 9, _asc(title), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(2)

    def sub_title(title: str) -> None:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        mc(6, title)
        pdf.set_font("Helvetica", "", 10)

    def kpi_row(items: List[tuple[str, str, tuple]]) -> None:
        """Render a horizontal strip of KPI boxes: [(label, value, rgb_color), ...]"""
        box_w = w / max(len(items), 1)
        x0 = pdf.l_margin
        for label, val, color in items:
            pdf.set_fill_color(248, 250, 252)
            pdf.rect(x0, pdf.get_y(), box_w - 2, 18, style="F")
            pdf.set_xy(x0 + 2, pdf.get_y() + 2)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(*color)
            pdf.cell(box_w - 4, 7, _asc(val), align="C")
            pdf.set_xy(x0 + 2, pdf.get_y() + 7)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(box_w - 4, 5, _asc(label), align="C")
            x0 += box_w
        pdf.set_xy(pdf.l_margin, pdf.get_y() + 18 + 2)
        pdf.set_text_color(0, 0, 0)

    def embed_screenshot(raw_path: str, caption: str = "", *, thumb: bool = False) -> None:
        """
        Embed a screenshot image into the PDF with explicit coordinates.
        Checks available page space first and inserts a new page when needed
        so the image is never silently clipped or rendered off-canvas.
        """
        real = _resolve_screenshot_path(raw_path, screenshots_dir)
        if not real:
            pdf.set_font("Helvetica", "I", 8)
            mc(4, f"[Screenshot not available: {_asc(raw_path, 80)}]", color=(130, 130, 130))
            return
        try:
            from PIL import Image as _PILImage  # noqa: PLC0415
            with _PILImage.open(real) as _pil:
                orig_w_px, orig_h_px = _pil.size
            # Compute display dimensions in mm (fpdf default DPI = 96)
            max_w = min(w * 0.45, 90) if thumb else min(w * 0.88, 155)
            img_w_mm = max_w
            ratio = orig_h_px / orig_w_px if orig_w_px else 1
            img_h_mm = img_w_mm * ratio
            if thumb:
                img_h_mm = min(img_h_mm, 55)
        except Exception:
            img_w_mm = min(w * 0.45, 90) if thumb else min(w * 0.88, 155)
            img_h_mm = 45 if thumb else 80  # fallback estimate

        # Reserve space: if less than img_h_mm + 20 mm left on page, break now
        space_left = pdf.h - pdf.b_margin - pdf.get_y()
        if space_left < min(img_h_mm + 14, 80):
            pdf.add_page()

        try:
            cur_y = pdf.get_y()
            pdf.set_x(pdf.l_margin)
            pdf.image(real, x=pdf.l_margin, y=cur_y, w=img_w_mm)
            # Advance cursor past the image
            pdf.set_xy(pdf.l_margin, cur_y + img_h_mm + 1)
            if caption:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)
                mc(4, f"  {_asc(caption)}")
                pdf.set_text_color(0, 0, 0)
            pdf.ln(4)
        except Exception as exc:
            pdf.set_font("Helvetica", "I", 8)
            mc(4, f"[Could not embed screenshot: {_asc(str(exc), 180)}]", color=(180, 100, 100))

    def render_ai_adaptation_block(original: str, adaptation: str) -> None:
        """Mirror the UI 'AI INTELLIGENCE: STEP ADAPTATION' panel."""
        fill_band(
            "  AI INTELLIGENCE: STEP ADAPTATION",
            height=6,
            fill=(250, 245, 255),
            color=(88, 28, 135),
            font_size=9,
        )
        pdf.set_font("Helvetica", "B", 8)
        mc(5, "  Original Intent:", color=(126, 34, 206))
        pdf.set_font("Helvetica", "I", 8)
        mc(5, f'  "{_asc(original[:500])}"', color=(107, 33, 168))
        pdf.set_font("Helvetica", "B", 8)
        mc(5, "  AI Correction:", color=(126, 34, 206))
        pdf.set_font("Helvetica", "", 8)
        mc(5, f"  {_asc(adaptation[:800])}", color=(76, 29, 149))
        pdf.ln(2)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pass_rate = round(passed_tests / total_tests * 100) if total_tests else 0
    from features.functional.services.run_outcome import (
        display_run_status,
        report_outcome_headline,
    )
    display = display_run_status(
        run_status, passed=passed_tests, failed=failed_tests, total=total_tests
    )
    status_color = _status_color(display["status"] if display["tone"] != "danger" else "failed")
    if display["tone"] == "success":
        status_color = (22, 163, 74)
    wall = _wall_clock(run_started_at, run_completed_at)
    sum_case_ms = sum(int(r.get("duration_ms") or 0) for r in results)
    headline, _tone = report_outcome_headline(passed_tests, failed_tests, total_tests)

    # ------------------------------------------------------------------
    # 1. COVER PAGE
    # ------------------------------------------------------------------
    pdf.add_page()

    # Large title
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(17, 24, 39)
    pdf.cell(0, 14, "Test Execution Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(75, 85, 99)
    pdf.cell(0, 6, _asc(project_name, 120), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0,
        6,
        _asc(f"Format: {fmt.upper()}  |  {'Summary + failures' if fmt == 'short' else 'Full evidence dump'}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)
    pdf.set_text_color(0, 0, 0)

    # Status badge — majority-pass shows Passed, not Failed
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*status_color)
    pdf.cell(0, 7, _asc(f"Status: {display['label']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    mc(5, headline, color=(55, 65, 81))
    pdf.ln(2)

    divider()

    # Run metadata table
    pdf.set_font("Helvetica", "B", 10)
    meta_rows = [
        ("Run number",   f"#{run_number}"),
        ("Run name",     run_name or "-"),
        ("Browser",      run_browser or "chromium"),
        ("Started",      _fmt_dt(run_started_at)),
        ("Completed",    _fmt_dt(run_completed_at)),
        ("Wall-clock",   wall),
        ("Sum of case times", _fmt_ms(sum_case_ms) + " (shared sessions may overlap)"),
        ("Report generated",  now_str),
    ]
    for label, val in meta_rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(55, 6, _asc(label), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, _asc(val, 200), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    divider()

    # KPI strip — pass rate color reflects health, not "any fail = red"
    error_count = sum(1 for r in results if r.get("status") == "error")
    kpi_row([
        ("Total Tests",  str(total_tests),     (99, 102, 241)),
        ("Passed",       str(passed_tests),     (22, 163, 74)),
        ("Failed",       str(failed_tests),     (220, 38, 38)),
        ("Skipped",      str(skipped_tests),    (107, 114, 128)),
        ("Pass Rate",    f"{pass_rate}%",       _pass_rate_color(pass_rate)),
    ])

    if error_count:
        pdf.set_font("Helvetica", "I", 9)
        mc(5, f"Note: {error_count} test(s) ended with an execution error (counted in Failed).",
           color=(150, 100, 0))

    pdf.ln(4)
    divider()

    # Coverage overview
    story_ids_covered = {r["test_case"]["user_story_id"] for r in results if r.get("test_case") and r["test_case"].get("user_story_id")}
    req_ids_covered = {r["test_case"]["requirement_id"] for r in results if r.get("test_case") and r["test_case"].get("requirement_id")}
    shot_steps = sum(
        1
        for r in results
        for s in (r.get("step_results") or [])
        if isinstance(s, dict) and s.get("screenshot_path")
    )

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Coverage at a glance", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"  User stories covered:   {len(story_ids_covered)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"  Requirements linked:    {len(req_ids_covered)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"  Test cases executed:    {len(results)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"  Step screenshots:       {shot_steps}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if fmt == "short":
        pdf.set_font("Helvetica", "I", 9)
        mc(
            5,
            "Short report: full per-case step dumps and agent logs are omitted. "
            "Generate a Long report for complete evidence.",
            color=(100, 100, 100),
        )

    # ------------------------------------------------------------------
    # 1b. RESULTS INDEX (compact table — what POs scan first)
    # ------------------------------------------------------------------
    pdf.add_page()
    section_title("Results Index")
    pdf.set_font("Helvetica", "", 9)
    mc(5, "Quick scan of every case in this run. Failed cases are listed first.")
    pdf.ln(2)

    ordered = sorted(
        results,
        key=lambda r: (0 if (r.get("status") or "") in ("failed", "error") else 1, r.get("id") or 0),
    )
    # Table header
    col_tc, col_st, col_dur, col_steps = 12, 22, 18, 14
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(col_tc, 6, "TC#", fill=True)
    pdf.cell(col_st, 6, "Status", fill=True)
    pdf.cell(col_dur, 6, "Duration", fill=True)
    pdf.cell(col_steps, 6, "Steps", fill=True)
    pdf.cell(0, 6, "Title", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 8)

    title_w = max(40.0, w - (col_tc + col_st + col_dur + col_steps))
    for r in ordered:
        tc = r.get("test_case") or {}
        st = (r.get("status") or "?").lower()
        clr = _status_color(st)
        steps = r.get("step_results") or []
        steps_ok = sum(1 for s in steps if isinstance(s, dict) and s.get("status") == "passed")
        steps_n = len(steps) if steps else 0
        title = _asc((tc.get("title") or "Untitled"), 90)
        # Estimate wrapped title height so rows never overlap
        title_lines = max(1, (len(title) // 48) + 1)
        row_h = max(5.5, 4.2 * min(title_lines, 3))
        if pdf.get_y() + row_h > pdf.h - 22:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(241, 245, 249)
            pdf.cell(col_tc, 6, "TC#", fill=True)
            pdf.cell(col_st, 6, "Status", fill=True)
            pdf.cell(col_dur, 6, "Duration", fill=True)
            pdf.cell(col_steps, 6, "Steps", fill=True)
            pdf.cell(0, 6, "Title", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 8)
        y0 = pdf.get_y()
        pdf.set_text_color(*clr)
        pdf.cell(col_tc, row_h, f"#{tc.get('case_number', '?')}")
        pdf.cell(col_st, row_h, st.upper()[:10])
        pdf.set_text_color(55, 65, 81)
        pdf.cell(col_dur, row_h, _fmt_ms(r.get("duration_ms")))
        pdf.cell(col_steps, row_h, f"{steps_ok}/{steps_n}" if steps_n else "-")
        pdf.set_text_color(17, 24, 39)
        x_title = pdf.get_x()
        pdf.multi_cell(
            title_w,
            4.2,
            title,
            align=align_l,
            new_x=XPos.LMARGIN,
            new_y=YPos.TOP,
            wrapmode=wm,
        )
        pdf.set_xy(pdf.l_margin, y0 + row_h)
    pdf.set_text_color(0, 0, 0)

    # ------------------------------------------------------------------
    # 2. REQUIREMENTS (BRDs) SECTION  (long format only)
    # ------------------------------------------------------------------
    if fmt == "long" and requirements:
        pdf.add_page()
        section_title("Requirements / BRD Documents")
        pdf.set_font("Helvetica", "", 10)
        mc(5, "The following requirement documents are linked to test cases in this run.")
        pdf.ln(3)

        for req_id, req in sorted(requirements.items()):
            sub_title(f"REQ-{req_id}: {req.get('title') or req.get('file_name') or 'Untitled'}")
            if req.get("file_name"):
                pdf.set_font("Helvetica", "I", 9)
                mc(4, f"File: {req['file_name']}", color=(100, 100, 100))
            # Count test cases linked to this requirement
            linked = [r for r in results if r.get("test_case") and r["test_case"].get("requirement_id") == req_id]
            pdf.set_font("Helvetica", "", 10)
            mc(5, f"Test cases in this run: {len(linked)}")
            pdf.ln(2)

    # ------------------------------------------------------------------
    # 3. USER STORIES SECTION  (long format only)
    # ------------------------------------------------------------------
    if fmt == "long" and user_stories:
        pdf.add_page()
        section_title("User Stories")
        pdf.set_font("Helvetica", "", 10)
        mc(5, "Test case results grouped by user story.")
        pdf.ln(3)

        for story_id, story in sorted(user_stories.items()):
            story_results = [r for r in results if r.get("test_case") and r["test_case"].get("user_story_id") == story_id]
            story_pass = sum(1 for r in story_results if r.get("status") == "passed")
            story_fail = len(story_results) - story_pass
            color = (22, 163, 74) if story_fail == 0 else (220, 38, 38)

            key_str = story.get("external_key") or f"US-{story_id}"
            sub_title(f"{key_str}: {story.get('title') or 'Untitled'}")

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*color)
            pdf.cell(0, 5, f"  Results: {story_pass} passed, {story_fail} failed (of {len(story_results)})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 9)

            if story.get("description"):
                mc(4, story["description"][:400], color=(75, 85, 99))
            if story.get("acceptance_criteria"):
                pdf.set_font("Helvetica", "B", 9)
                mc(4, "Acceptance criteria:")
                pdf.set_font("Helvetica", "", 9)
                mc(4, story["acceptance_criteria"][:500])
            if story.get("status"):
                mc(4, f"Story status: {story['status']} | Priority: {story.get('priority', '-')}")

            # Mini table of test cases
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(241, 245, 249)
            pdf.cell(14, 6, "TC#", fill=True)
            pdf.cell(0, 6, "Title", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 9)
            for r in story_results:
                tc = r.get("test_case", {})
                st = r.get("status", "?")
                clr = _status_color(st)
                pdf.set_text_color(*clr)
                pdf.cell(14, 5, f"  #{tc.get('case_number', '?')}")
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, f"[{st.upper()}]  {_asc(tc.get('title', ''), 120)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(4)

    # ------------------------------------------------------------------
    # 4. EXECUTION DETAILS (per test case) — long format only
    # Short reports skip this to avoid 1000+ page dumps; use Failures Digest instead.
    # ------------------------------------------------------------------
    if fmt == "long":
        pdf.add_page()
        section_title("Test Execution Details")
        pdf.set_font("Helvetica", "", 10)
        mc(5, "Full execution detail for every test case, including steps and screenshots.")

        def _parse_verdict_json(raw: str):
            import json as _json
            import re as _re
            marker = "VERDICT_JSON_START"
            if marker not in (raw or ""):
                return None
            start_i = raw.index(marker) + len(marker)
            chunk = raw[start_i:].strip()
            brace_depth = 0
            buf = ""
            in_str = False
            esc = False
            for ch in chunk:
                if esc:
                    buf += ch
                    esc = False
                    continue
                if ch == "\\" and in_str:
                    buf += ch
                    esc = True
                    continue
                if ch == '"' and not esc:
                    in_str = not in_str
                if not in_str:
                    if ch == "{":
                        brace_depth += 1
                    elif ch == "}":
                        brace_depth -= 1
                buf += ch
                if brace_depth == 0 and buf.strip().startswith("{"):
                    break
            try:
                obj = _json.loads(buf.strip())
                steps = obj.get("steps") or []
                if steps:
                    return steps
            except Exception:
                pass
            steps_fallback = []
            for m in _re.finditer(r"\{[^{}]{0,2000}\}", chunk, _re.DOTALL):
                try:
                    obj = _json.loads(m.group())
                    if "step_number" in obj:
                        steps_fallback.append(obj)
                except Exception:
                    pass
            if steps_fallback:
                steps_fallback.sort(key=lambda s: s.get("step_number", 0))
                return steps_fallback
            return None

        for idx, r in enumerate(results, 1):
          tc = r.get("test_case") or {}
          status = r.get("status", "unknown")
          st_color = _status_color(status)

          pdf.ln(4)
          # ── Case header band ──────────────────────────────────────────────────
          pdf.set_fill_color(248, 250, 252)
          pdf.set_font("Helvetica", "B", 11)
          pdf.set_text_color(*st_color)
          pdf.cell(18, 10, f"#{tc.get('case_number', idx)}", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
          pdf.set_text_color(17, 24, 39)
          pdf.cell(0, 10, _asc(tc.get("title", "Untitled"), 150), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
          pdf.set_text_color(0, 0, 0)

          # Meta row
          pdf.set_font("Helvetica", "", 9)
          pdf.set_text_color(75, 85, 99)
          step_shots = sum(
              1 for s in (r.get("step_results") or [])
              if isinstance(s, dict) and s.get("screenshot_path")
          )
          meta_parts = [
              f"Status: {status.upper()}",
              f"Duration: {_fmt_ms(r.get('duration_ms'))}",
              f"Priority: {tc.get('priority', '-')}",
              f"Category: {tc.get('category', '-')}",
              f"Screenshots: {step_shots}",
          ]
          if tc.get("scenario_type"):
              meta_parts.append(f"Scenario: {tc['scenario_type']}")
          mc(4, "  " + "   |   ".join(meta_parts))
          pdf.set_text_color(0, 0, 0)

          # Preconditions
          if tc.get("preconditions"):
              pdf.set_font("Helvetica", "B", 9)
              mc(4, "  Preconditions:")
              pdf.set_font("Helvetica", "I", 9)
              mc(4, f"  {tc['preconditions'][:400]}", color=(75, 85, 99))

          # Description
          if tc.get("description"):
              pdf.set_font("Helvetica", "I", 9)
              mc(4, f"  {tc['description'][:500]}", color=(100, 100, 100))
              pdf.set_font("Helvetica", "", 9)

          # ── Step execution results (vertical flow — mirrors UI accordion) ─────
          defined_steps = {
              int(s.get("step_number", 0)): s
              for s in (tc.get("steps") or [])
              if isinstance(s, dict) and s.get("step_number") is not None
          }
          original_steps_map: Dict[int, Dict[str, Any]] = {}
          for os_item in (r.get("original_steps") or []):
              if isinstance(os_item, dict):
                  sn = os_item.get("step_number") or os_item.get("step")
                  if sn is not None:
                      original_steps_map[int(sn)] = os_item

          step_results_map: Dict[int, Dict[str, Any]] = {}
          for sr in (r.get("step_results") or []):
              if isinstance(sr, dict):
                  sn = sr.get("step_number") or sr.get("step")
                  if sn is not None:
                      step_results_map[int(sn)] = sr

          # Merge persisted step_results with test-case definitions so we always
          # have a complete vertical list (avoids the broken horizontal table).
          all_step_nums = sorted(set(defined_steps.keys()) | set(step_results_map.keys()))
          step_results_list: List[Dict[str, Any]] = []
          failed_at = r.get("failed_step")
          for sn in all_step_nums:
              sr = step_results_map.get(sn, {})
              defined = defined_steps.get(sn, {})
              inferred_status = (sr.get("status") or "").lower()
              if not inferred_status:
                  if failed_at and int(sn) == int(failed_at):
                      inferred_status = "failed"
                  elif failed_at and int(sn) < int(failed_at):
                      inferred_status = "passed"
                  elif status in ("failed", "error"):
                      inferred_status = "failed"
                  else:
                      inferred_status = status
              action_bits = " ".join(
                  str(defined.get(k, "") or "")
                  for k in ("action", "target", "description")
              ).strip()
              step_results_list.append({
                  "step_number": sn,
                  "status": inferred_status,
                  "description": (
                      sr.get("description")
                      or original_steps_map.get(sn, {}).get("description")
                      or defined.get("description")
                      or action_bits
                      or "-"
                  ),
                  "actual_result": sr.get("actual_result") or defined.get("expected_result") or "-",
                  "adaptation": sr.get("adaptation"),
                  "screenshot_path": sr.get("screenshot_path"),
                  "error": sr.get("error"),
                  "agent_actions": sr.get("agent_actions") or [],
                  "verdict_source": sr.get("verdict_source"),
              })

          if step_results_list:
              pdf.ln(2)
              pdf.set_font("Helvetica", "B", 10)
              mc(5, "Step Execution Results")
              pdf.set_font("Helvetica", "", 9)

              for sr in step_results_list:
                  sn = int(sr.get("step_number") or 0)
                  sr_status = (sr.get("status") or "").lower()
                  sr_color = _status_color(sr_status) if sr_status else (100, 100, 100)
                  original_desc = str(sr.get("description") or "-")
                  actual = str(sr.get("actual_result") or "-")
                  adaptation = (sr.get("adaptation") or "").strip()

                  step_hdr = f"  Step {sn}  [{sr_status.upper() or 'UNKNOWN'}]"
                  if adaptation:
                      step_hdr += "  [AI ADAPTED]"
                  vs = (sr.get("verdict_source") or "").strip()
                  if vs.startswith("inferred"):
                      step_hdr += "  [INFERRED]"
                  elif vs == "explicit":
                      step_hdr += "  [EXPLICIT]"
                  fill_band(step_hdr, height=7, fill=(248, 250, 252), color=sr_color, font_size=9)

                  pdf.set_font("Helvetica", "I", 8)
                  mc(5, f"  Original: {_asc(original_desc[:500])}", color=(75, 85, 99))
                  pdf.set_font("Helvetica", "", 9)
                  mc(5, f"  Actual: {_asc(actual[:800])}")

                  actions = sr.get("agent_actions") or []
                  if actions:
                      pdf.set_font("Helvetica", "B", 8)
                      mc(4, "  Browser actions:", color=(75, 85, 99))
                      pdf.set_font("Helvetica", "", 8)
                      for a in actions[:5]:
                          # Keep action lines short — long agent prose blows page count
                          mc(4, f"    * {_asc(_wrap(str(a), 42)[:160])}", color=(55, 65, 81))

                  if sr.get("error"):
                      mc(5, f"  Error: {_asc(str(sr['error'])[:400])}", color=(180, 50, 50))

                  if adaptation:
                      render_ai_adaptation_block(original_desc, adaptation)

                  if sr.get("screenshot_path"):
                      embed_screenshot(
                          sr["screenshot_path"],
                          f"TC-{tc.get('case_number', idx)} Step {sn} [{sr_status.upper() or 'SHOT'}]",
                      )
                  pdf.ln(3)

          # ── Adapted steps summary (dedicated adapted_steps array) ─────────────
          adapted_steps = [
              s for s in (r.get("adapted_steps") or [])
              if isinstance(s, dict) and (s.get("adaptation") or "").strip()
          ]
          if adapted_steps:
              pdf.ln(2)
              fill_band(
                  f"AI Adapted Steps Summary ({len(adapted_steps)} step(s))",
                  height=8,
                  fill=(237, 233, 254),
                  color=(67, 56, 202),
                  font_size=10,
              )
              pdf.ln(1)
              for ad in adapted_steps:
                  sn = ad.get("step_number") or ad.get("step") or "?"
                  orig = ad.get("description") or original_steps_map.get(int(sn) if str(sn).isdigit() else 0, {}).get("description", "-")
                  adapt = ad.get("adaptation") or ""
                  pdf.set_font("Helvetica", "B", 9)
                  mc(5, f"  Step {sn}")
                  render_ai_adaptation_block(str(orig), str(adapt))

          # ── Error summary ────────────────────────────────────────────────────
          raw_err = r.get("error_message") or ""
          if status in ("failed", "error") and raw_err:
              # Try to parse VERDICT_JSON for richer step-by-step display
              verdict_steps = _parse_verdict_json(raw_err)
              if verdict_steps:
                  pdf.ln(2)
                  pdf.set_font("Helvetica", "B", 9)
                  mc(4, "AI Step Verdict:")
                  pdf.set_font("Helvetica", "", 9)
                  for vs in verdict_steps:
                      snum = vs.get("step_number", "?")
                      vstatus = (vs.get("status") or "").upper()
                      vcolor = _status_color((vs.get("status") or "").lower())
                      pdf.set_text_color(*vcolor)
                      mc(4, f"  Step {snum} - {vstatus}")
                      pdf.set_text_color(0, 0, 0)
                      if vs.get("actual_result"):
                          mc(6, f"  Actual: {_asc(vs['actual_result'][:300])}", color=(60, 60, 60))
                      if vs.get("adaptation"):
                          pdf.set_font("Helvetica", "I", 9)
                          mc(6, f"  AI Adaptation: {_asc(vs['adaptation'][:400])}", color=(80, 60, 130))
                          pdf.set_font("Helvetica", "", 9)
              else:
                  # Plain error (strip VERDICT_JSON noise)
                  clean_err = raw_err
                  if "VERDICT_JSON_START" in clean_err:
                      clean_err = clean_err[:clean_err.index("VERDICT_JSON_START")].strip()
                  if clean_err:
                      pdf.ln(2)
                      pdf.set_font("Helvetica", "B", 9)
                      pdf.set_text_color(180, 50, 50)
                      mc(4, "Error:")
                      pdf.set_font("Helvetica", "", 9)
                      mc(4, f"  {clean_err[:1000]}", color=(180, 50, 50))
                      pdf.set_text_color(0, 0, 0)

          # ── AI Agent Iteration Log ─────────────────────────────────────────
          agent_logs = [
              alog for alog in (r.get("agent_logs") or [])
              if isinstance(alog, dict)
          ]
          if agent_logs:
              pdf.ln(3)
              fill_band(
                  f"AI Agent Execution Log  ({len(agent_logs)} iterations)",
                  height=8,
                  fill=(237, 233, 254),
                  color=(67, 56, 202),
                  font_size=10,
              )
              pdf.ln(1)

              for iter_idx, alog in enumerate(agent_logs, 1):
                  step_ref = alog.get("agent_step") or alog.get("step_number") or iter_idx
                  iter_status = (alog.get("status") or "").lower()
                  iter_color = _status_color(iter_status) if iter_status else (80, 80, 80)

                  step_label = f"  Iteration {iter_idx}  |  Agent Step: {step_ref}"
                  if iter_status:
                      step_label += f"  [{iter_status.upper()}]"
                  if alog.get("timestamp"):
                      step_label += f"  @ {_asc(str(alog['timestamp'])[:19])}"
                  fill_band(
                      step_label,
                      height=7,
                      fill=(245, 243, 255),
                      color=iter_color,
                      font_size=9,
                  )
                  pdf.set_font("Helvetica", "", 9)

                  # What the agent thought / observed / did
                  desc = alog.get("description") or alog.get("thought") or alog.get("observation") or ""
                  if desc:
                      pdf.set_font("Helvetica", "B", 9)
                      mc(6, "  Agent:", color=(30, 30, 30))
                      pdf.set_font("Helvetica", "", 9)
                      mc(8, _asc(desc[:1200]), color=(40, 40, 60))

                  # Action performed
                  action = alog.get("action") or alog.get("action_performed") or ""
                  if action and isinstance(action, str):
                      pdf.set_font("Helvetica", "B", 9)
                      mc(6, "  Action:", color=(30, 30, 30))
                      pdf.set_font("Helvetica", "", 9)
                      mc(8, _asc(action[:600]), color=(40, 60, 40))
                  elif action and isinstance(action, dict):
                      pdf.set_font("Helvetica", "B", 9)
                      mc(6, "  Action:", color=(30, 30, 30))
                      pdf.set_font("Helvetica", "", 9)
                      for k, v in action.items():
                          mc(10, _asc(f"{k}: {v}", 200), color=(40, 60, 40))

                  # AI adaptation — the key "what we did differently"
                  adaptation = alog.get("adaptation") or alog.get("adaptation_note") or ""
                  if adaptation:
                      fill_band(
                          "  AI Adaptation:",
                          height=6,
                          fill=(254, 252, 232),
                          color=(120, 80, 0),
                          font_size=9,
                      )
                      pdf.set_font("Helvetica", "I", 9)
                      mc(5, _asc(f"  {adaptation[:1000]}"), color=(100, 60, 0))

                  # Result / actual outcome of this iteration
                  actual = alog.get("actual_result") or alog.get("result") or ""
                  if actual:
                      pdf.set_font("Helvetica", "B", 9)
                      mc(6, "  Result:", color=(30, 30, 30))
                      pdf.set_font("Helvetica", "", 9)
                      mc(8, _asc(actual[:600]), color=(60, 60, 60))

                  # Error at this iteration level
                  iter_err = alog.get("error") or alog.get("error_message") or ""
                  if iter_err:
                      pdf.set_font("Helvetica", "", 9)
                      mc(8, _asc(f"  Error: {iter_err}", 400), color=(180, 50, 50))

                  # Screenshot for this iteration
                  shot = alog.get("screenshot_path") or alog.get("screenshot") or ""
                  if shot:
                      embed_screenshot(shot, f"Iteration {iter_idx} - step {step_ref}")

                  pdf.ln(2)

          # ── Primary / final screenshot ────────────────────────────────────
          primary_shot = r.get("screenshot_path")
          # If no dedicated result screenshot, use the LAST agent log screenshot
          if not primary_shot:
              for alog in reversed(agent_logs):
                  if isinstance(alog, dict) and alog.get("screenshot_path"):
                      primary_shot = alog["screenshot_path"]
                      break

          if primary_shot and not agent_logs:
              # Only show standalone if there are no agent_logs (agent_logs already shows it)
              pdf.ln(2)
              pdf.set_font("Helvetica", "B", 9)
              mc(4, "Screenshot evidence:")
              embed_screenshot(primary_shot, f"TC-{tc.get('case_number', idx)} - {status}")
          elif primary_shot and agent_logs:
              # Already embedded per-iteration; still show final result screenshot if different
              last_agent_shot = ""
              for alog in reversed(agent_logs):
                  if isinstance(alog, dict) and alog.get("screenshot_path"):
                      last_agent_shot = alog["screenshot_path"]
                      break
              if primary_shot != last_agent_shot:
                  pdf.ln(2)
                  pdf.set_font("Helvetica", "B", 9)
                  mc(4, "Final result screenshot:")
                  embed_screenshot(primary_shot, f"TC-{tc.get('case_number', idx)} final - {status}")

          pdf.ln(4)
          pdf.set_draw_color(220, 220, 230)
          pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    # ------------------------------------------------------------------
    # 5. FAILURES DIGEST
    # ------------------------------------------------------------------
    failures = [r for r in results if r.get("status") in ("failed", "error")]
    if failures:
        pdf.add_page()
        section_title(f"Failures Digest ({len(failures)} cases)")
        pdf.set_font("Helvetica", "", 10)
        mc(
            5,
            "All failed and error test cases consolidated for triage. "
            "Each entry includes the failing step, observed result, and evidence screenshot when available.",
        )
        pdf.ln(3)

        for r in failures:
            tc = r.get("test_case") or {}
            status = r.get("status", "failed")
            clr = _status_color(status)

            sub_title(f"TC-{tc.get('case_number', '?')}: {tc.get('title', 'Untitled')}")

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*clr)
            pdf.cell(
                0,
                5,
                _asc(
                    f"  {status.upper()} - failed at step {r.get('failed_step', '?')} - {_fmt_ms(r.get('duration_ms'))}"
                ),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.set_text_color(0, 0, 0)

            # Prefer the failing step's actual_result over raw error_message noise
            fail_step = r.get("failed_step")
            fail_actual = None
            fail_shot = None
            for sr in (r.get("step_results") or []):
                if not isinstance(sr, dict):
                    continue
                sn = sr.get("step_number")
                if fail_step is not None and sn == fail_step:
                    fail_actual = sr.get("actual_result")
                    fail_shot = sr.get("screenshot_path")
                    break
            if not fail_actual:
                for sr in (r.get("step_results") or []):
                    if isinstance(sr, dict) and sr.get("status") not in ("passed", None):
                        fail_actual = sr.get("actual_result")
                        fail_shot = fail_shot or sr.get("screenshot_path")
                        break

            if fail_actual:
                pdf.set_font("Helvetica", "", 9)
                mc(4, f"  Observed: {_asc(str(fail_actual)[:700])}", color=(127, 29, 29))

            if r.get("error_message"):
                clean_err = r["error_message"]
                if "VERDICT_JSON_START" in clean_err:
                    clean_err = clean_err[: clean_err.index("VERDICT_JSON_START")].strip()
                if clean_err and clean_err != fail_actual:
                    pdf.set_font("Helvetica", "", 9)
                    mc(4, f"  Error: {_asc(clean_err[:500])}", color=(180, 50, 50))

            if fail_shot:
                embed_screenshot(
                    fail_shot,
                    f"TC-{tc.get('case_number', '?')} failure evidence",
                    thumb=True,
                )
            elif r.get("screenshot_path"):
                embed_screenshot(
                    r["screenshot_path"],
                    f"TC-{tc.get('case_number', '?')} primary snapshot",
                    thumb=True,
                )

            # Linked story
            story_id = tc.get("user_story_id")
            if story_id and story_id in user_stories:
                us = user_stories[story_id]
                pdf.set_font("Helvetica", "I", 9)
                key_str = us.get("external_key") or f"US-{story_id}"
                mc(4, f"  User story: {key_str} - {us.get('title', '')}", color=(80, 80, 80))

            pdf.ln(3)

    # ------------------------------------------------------------------
    # 6. SCREENSHOT APPENDIX (long format only)
    # ------------------------------------------------------------------
    if fmt == "long":
        screenshot_entries: List[Dict[str, str]] = []
        seen_shots: set[str] = set()

        def _add_shot(path: str, label: str) -> None:
            if not path or path in seen_shots:
                return
            seen_shots.add(path)
            screenshot_entries.append({"path": path, "label": label})

        for r in results:
            tc = r.get("test_case") or {}
            tc_num = tc.get("case_number", "?")
            status = (r.get("status") or "").upper()

            for sr in (r.get("step_results") or []):
                if isinstance(sr, dict) and sr.get("screenshot_path"):
                    sn = sr.get("step_number") or sr.get("step") or "?"
                    st = (sr.get("status") or "").upper()
                    _add_shot(
                        sr["screenshot_path"],
                        f"TC-{tc_num} Step {sn} [{st}]",
                    )

            for iter_idx, alog in enumerate(r.get("agent_logs") or [], 1):
                if isinstance(alog, dict) and alog.get("screenshot_path"):
                    step_ref = alog.get("agent_step") or alog.get("step_number") or iter_idx
                    _add_shot(
                        alog["screenshot_path"],
                        f"TC-{tc_num} Agent iter {iter_idx} step {step_ref}",
                    )

            if r.get("screenshot_path"):
                _add_shot(
                    r["screenshot_path"],
                    f"TC-{tc_num} Run snapshot [{status}]",
                )

        if screenshot_entries:
            pdf.add_page()
            section_title(f"Screenshot Appendix ({len(screenshot_entries)} images)")
            pdf.set_font("Helvetica", "", 9)
            mc(5, "Visual evidence captured during this run. Each entry shows the image and its context.")
            pdf.ln(2)
            for i, entry in enumerate(screenshot_entries, 1):
                resolved = _resolve_screenshot_path(entry["path"], screenshots_dir)
                fname = Path(entry["path"]).name
                pdf.set_font("Helvetica", "B", 9)
                status_tag = "[OK]" if resolved else "[MISSING]"
                mc(5, f"  {i:3d}. {status_tag} {_asc(entry['label'])}")
                pdf.set_font("Helvetica", "I", 8)
                mc(4, f"      File: {_asc(fname)}", color=(100, 100, 100))
                if resolved:
                    embed_screenshot(entry["path"], entry["label"], thumb=True)
                else:
                    pdf.set_font("Helvetica", "I", 8)
                    mc(4, f"      [Image file not found on disk: {_asc(entry['path'], 120)}]", color=(180, 100, 100))
                pdf.ln(2)


    # Output
    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return bytes(raw)
