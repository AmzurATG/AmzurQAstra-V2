"""Build Jira bug payload (summary, description, screenshots) from a failed TestResult."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from features.functional.core.case_budget import format_duration_ms


MAX_SCREENSHOTS = 8


def is_eligible_for_jira_bug(
    *,
    status: str,
    infra_error: bool = False,
    ai_modified: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Return (ok, reason). Only real app failures may be filed."""
    st = (status or "").lower()
    infra = bool(infra_error) or bool((ai_modified or {}).get("infra_error"))
    if infra or st == "error":
        return False, "Infrastructure / blocked results cannot be logged as product bugs."
    if st != "failed":
        return False, "Only failed test results can be logged to Jira."
    return True, ""


def _basename(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(str(path)).name


def resolve_screenshot_paths(
    *,
    screenshot_path: Optional[str] = None,
    agent_logs: Optional[List[Dict[str, Any]]] = None,
    max_files: int = MAX_SCREENSHOTS,
) -> List[Path]:
    """Resolve local screenshot files under SCREENSHOTS_DIR (evidence-first)."""
    names: List[str] = []
    seen: set[str] = set()

    def _add(raw: Optional[str]) -> None:
        name = _basename(raw)
        if not name or name in seen:
            return
        seen.add(name)
        names.append(name)

    _add(screenshot_path)
    logs = list(agent_logs or [])
    evidence = [
        e
        for e in logs
        if isinstance(e, dict) and e.get("screenshot_path") and e.get("evidence") is True
    ]
    if evidence:
        for e in evidence:
            _add(e.get("screenshot_path"))
    else:
        for e in logs:
            if isinstance(e, dict) and e.get("screenshot_path") and e.get("evidence", True) is not False:
                _add(e.get("screenshot_path"))

    root = Path(settings.SCREENSHOTS_DIR)
    out: List[Path] = []
    for name in names:
        if len(out) >= max_files:
            break
        fp = root / name
        if fp.is_file():
            out.append(fp)
    return out


def build_bug_summary(title: str) -> str:
    t = (title or "Test case").strip() or "Test case"
    return f"[QAstra] {t} failed"[:255]


def build_bug_description(
    *,
    title: str,
    run_number: Optional[int] = None,
    run_id: Optional[int] = None,
    app_url: Optional[str] = None,
    duration_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    user_message: Optional[str] = None,
    step_results: Optional[List[Dict[str, Any]]] = None,
    original_steps: Optional[List[Dict[str, Any]]] = None,
    related_story_key: Optional[str] = None,
) -> str:
    """Jira wiki-markup description with repro steps and environment."""
    steps = list(step_results or []) or list(original_steps or [])
    lines: List[str] = []
    lines.append("h2. Summary")
    run_label = f"#{run_number}" if run_number else (f"id {run_id}" if run_id else "n/a")
    lines.append(f"Automated test *{title or 'Untitled'}* failed in QAstra run {run_label}.")
    if related_story_key:
        lines.append(f"Related story: [{related_story_key}|{related_story_key}]")
    lines.append("")

    lines.append("h2. Steps to Reproduce")
    if not steps:
        lines.append("# Open the application under test")
        lines.append("# Execute the test case as defined in QAstra")
        lines.append("# Observe the failure")
    else:
        for i, s in enumerate(steps, start=1):
            if not isinstance(s, dict):
                continue
            sn = s.get("step_number", i)
            desc = (s.get("description") or s.get("action") or "Step").strip()
            st = (s.get("status") or "").lower()
            marker = " *(failed here)*" if st in ("failed", "error") else ""
            lines.append(f"# {sn}. {desc}{marker}")
    lines.append("")

    failed = next(
        (
            s
            for s in steps
            if isinstance(s, dict) and str(s.get("status") or "").lower() in ("failed", "error")
        ),
        None,
    )
    lines.append("h2. Expected")
    exp = ""
    if failed:
        exp = str(failed.get("expected_result") or "").strip()
    if not exp and steps:
        last = steps[-1] if isinstance(steps[-1], dict) else {}
        exp = str(last.get("expected_result") or "").strip()
    lines.append(exp or "_Not specified in the test case._")
    lines.append("")

    lines.append("h2. Actual")
    act = ""
    if failed:
        act = str(failed.get("actual_result") or "").strip()
    msg = (user_message or error_message or "").strip()
    if act:
        lines.append(act)
    elif msg:
        lines.append(msg)
    else:
        lines.append("_Test case failed without a detailed actual result._")
    lines.append("")

    if msg and msg != act:
        lines.append("h2. Error")
        lines.append("{code}")
        lines.append(msg[:4000])
        lines.append("{code}")
        lines.append("")

    lines.append("h2. Environment")
    lines.append(f"* App URL: {app_url or '—'}")
    lines.append(f"* QAstra run: {run_label}")
    lines.append(f"* Duration: {format_duration_ms(duration_ms)}")
    lines.append("* Evidence: screenshots attached (when available)")
    lines.append("")
    lines.append("_Filed automatically from QAstra._")
    return "\n".join(lines)


def build_jira_bug_draft(
    *,
    title: str,
    status: str,
    infra_error: bool = False,
    ai_modified: Optional[Dict[str, Any]] = None,
    run_number: Optional[int] = None,
    run_id: Optional[int] = None,
    app_url: Optional[str] = None,
    duration_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    step_results: Optional[List[Dict[str, Any]]] = None,
    original_steps: Optional[List[Dict[str, Any]]] = None,
    screenshot_path: Optional[str] = None,
    agent_logs: Optional[List[Dict[str, Any]]] = None,
    related_story_key: Optional[str] = None,
) -> Dict[str, Any]:
    ok, reason = is_eligible_for_jira_bug(
        status=status, infra_error=infra_error, ai_modified=ai_modified
    )
    if not ok:
        return {"eligible": False, "reason": reason}

    ai = ai_modified or {}
    user_message = ai.get("user_message")
    summary = build_bug_summary(title)
    description = build_bug_description(
        title=title,
        run_number=run_number,
        run_id=run_id,
        app_url=app_url,
        duration_ms=duration_ms,
        error_message=error_message,
        user_message=user_message,
        step_results=step_results,
        original_steps=original_steps,
        related_story_key=related_story_key,
    )
    paths = resolve_screenshot_paths(
        screenshot_path=screenshot_path,
        agent_logs=agent_logs,
    )
    return {
        "eligible": True,
        "summary": summary,
        "description": description,
        "screenshot_paths": [str(p) for p in paths],
        "related_story_key": related_story_key,
    }
