"""
Parse and validate test-case CSV (single file: cases + optional steps per row).

Format (UTF-8, header required) — documented for end users:
- One file; rows with the same case_key belong to one test case.
- Rows with no step action (and no step fields) create/update case metadata only — zero steps allowed.
- Multiple step rows share the same case_key; step_number optional (auto 1..n in file order per case).

See GET /functional/test-cases/csv-template for a downloadable example.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from features.functional.db.models.test_case import (
    TestCaseCategory,
    TestCasePriority,
    TestCaseStatus,
)
from features.functional.db.models.test_step import TestStepAction
from features.functional.schemas.test_case_import import CsvImportErrorItem

MAX_CSV_BYTES = 15 * 1024 * 1024  # 15 MiB
MAX_DATA_ROWS = 12_000


# Map common header aliases → canonical keys
HEADER_ALIASES: Dict[str, str] = {}
for canon, aliases in {
    "case_key": (
        "case_key",
        "casekey",
        "case_id",
        "caseid",
        "external_id",
        "externalid",
        "test_case_key",
    ),
    "title": ("title", "name", "test_case", "testcase", "summary"),
    "description": ("description", "desc", "details"),
    "preconditions": ("preconditions", "precondition", "prerequisites"),
    "priority": ("priority", "prio"),
    "category": ("category", "cat"),
    "status": ("status", "state"),
    "tags": ("tags", "labels"),
    "requirement_id": ("requirement_id", "requirementid", "req_id"),
    "user_story_id": ("user_story_id", "userstory_id", "story_id", "storyid"),
    "step_number": ("step_number", "step_no", "stepno", "seq", "#"),
    "action": ("action", "step_action", "act"),
    "target": ("target", "selector", "locator", "url"),
    "value": ("value", "input", "text"),
    "step_description": (
        "step_description",
        "step_desc",
        "instruction",
        "step_instructions",
        "step_instruction",
    ),
    "expected_result": ("expected_result", "expected", "expected_outcome"),
}.items():
    for a in aliases:
        HEADER_ALIASES[a.lower().strip()] = canon


VALID_PRIORITIES = {p.value for p in TestCasePriority}
VALID_CATEGORIES = {c.value for c in TestCaseCategory}
VALID_STATUSES = {s.value for s in TestCaseStatus}
VALID_ACTIONS = {a.value for a in TestStepAction}

ACTION_SYNONYMS = {
    "goto": "navigate",
    "open": "navigate",
    "nav": "navigate",
    "visit": "navigate",
    "input": "type",
    "enter": "type",
    "fill_in": "fill",
    "choose": "select",
    "tap": "click",
    "press": "click",
    "verify_text": "assert_text",
    "verify_visible": "assert_visible",
}


def _norm_header(h: str) -> Optional[str]:
    if h is None:
        return None
    key = h.strip().lower().replace(" ", "_").replace("-", "_")
    key = key.lstrip("\ufeff")
    if key in HEADER_ALIASES:
        return HEADER_ALIASES[key]
    # allow already-canonical names
    if key in {
        "case_key",
        "title",
        "description",
        "preconditions",
        "priority",
        "category",
        "status",
        "tags",
        "requirement_id",
        "user_story_id",
        "step_number",
        "action",
        "target",
        "value",
        "step_description",
        "expected_result",
    }:
        return key
    return None


def _cell(row: List[str], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return (row[idx] or "").strip()


@dataclass
class StepDraft:
    step_number: Optional[int]
    action: TestStepAction
    target: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    expected_result: Optional[str] = None
    source_row: int = 0


@dataclass
class CaseDraft:
    case_key: str
    title: Optional[str] = None
    description: Optional[str] = None
    preconditions: Optional[str] = None
    priority: TestCasePriority = TestCasePriority.medium
    category: TestCaseCategory = TestCaseCategory.regression
    status: TestCaseStatus = TestCaseStatus.draft
    tags: Optional[str] = None
    requirement_id: Optional[int] = None
    user_story_id: Optional[int] = None
    steps: List[StepDraft] = field(default_factory=list)
    source_rows: List[int] = field(default_factory=list)


def _parse_int(val: str, *, field_name: str, row: int, errors: List[CsvImportErrorItem]) -> Optional[int]:
    v = (val or "").strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        errors.append(CsvImportErrorItem(row=row, column=field_name, message=f"Invalid integer: {val!r}"))
        return None


def _parse_enum_str(
    val: str,
    allowed: set,
    default: str,
    *,
    field_name: str,
    row: int,
    errors: List[CsvImportErrorItem],
) -> str:
    v = (val or "").strip().lower()
    if not v:
        return default
    if v not in allowed:
        errors.append(CsvImportErrorItem(row=row, column=field_name, message=f"Invalid {field_name}: {val!r}; allowed: {sorted(allowed)}"))
        return "__invalid__"
    return v


def _normalize_action_token(raw: Optional[str]) -> Optional[str]:
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    s = ACTION_SYNONYMS.get(s, s)
    if s in VALID_ACTIONS:
        return s
    return None


def decode_csv_bytes(data: bytes) -> Tuple[str, List[CsvImportErrorItem]]:
    """Decode to text; UTF-8 with BOM first, then utf-8 strict, then replace errors as last resort."""
    warnings: List[CsvImportErrorItem] = []
    try:
        return data.decode("utf-8-sig"), warnings
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("utf-8"), warnings
    except UnicodeDecodeError:
        txt = data.decode("latin-1")
        warnings.append(
            CsvImportErrorItem(row=0, message="File decoded as Latin-1; prefer UTF-8 CSV from Excel (Save As CSV UTF-8).")
        )
        return txt, warnings


def _strip_leading_hash_lines(text: str) -> str:
    """Remove QAstra template comment lines (leading # only) so uploads need no manual edit."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].lstrip("\ufeff \t")
        if s.startswith("#"):
            i += 1
            continue
        break
    return "\n".join(lines[i:])


def parse_csv_to_rows(text: str) -> Tuple[List[Optional[str]], List[List[str]], List[CsvImportErrorItem]]:
    """Return (column_map aligned with indices, body_rows), warnings."""
    warnings: List[CsvImportErrorItem] = []
    text = _strip_leading_hash_lines(text or "")
    if not (text or "").strip():
        return [], [], [CsvImportErrorItem(row=1, message="File is empty.")]

    reader = csv.reader(io.StringIO(text))
    try:
        header_raw = next(reader)
    except StopIteration:
        return [], [], [CsvImportErrorItem(row=1, message="No header row.")]

    col_map: List[Optional[str]] = [_norm_header(h or "") for h in header_raw]
    if "case_key" not in col_map:
        return [], [], [CsvImportErrorItem(row=1, message="Missing required column: case_key (or alias e.g. case_id).")]

    body: List[List[str]] = []
    for row in reader:
        if not row or all(not (c or "").strip() for c in row):
            continue
        body.append(row)

    if len(body) > MAX_DATA_ROWS:
        return [], [], [CsvImportErrorItem(row=0, message=f"Too many data rows (max {MAX_DATA_ROWS}).")]

    return col_map, body, warnings


def row_to_dict(col_map: List[Optional[str]], raw: List[str], row_number: int) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for i, h in enumerate(col_map):
        if h is None:
            continue
        out[h] = _cell(raw, i)
    return out


def build_case_groups(
    col_map: List[Optional[str]],
    body: List[List[str]],
    errors: List[CsvImportErrorItem],
) -> Tuple[Dict[str, CaseDraft], List[CsvImportErrorItem]]:
    """Group rows by case_key; accumulate steps. Row numbers are 1-based CSV line (header=1, first data=2)."""

    def get(rdict: Dict[str, str], key: str) -> str:
        return (rdict.get(key) or "").strip()

    groups: Dict[str, CaseDraft] = {}
    data_start_row = 2

    for offset, raw in enumerate(body):
        row_num = data_start_row + offset
        rd = row_to_dict(col_map, raw, row_num)
        ck = get(rd, "case_key")
        if not ck:
            errors.append(CsvImportErrorItem(row=row_num, column="case_key", message="case_key is required on every non-empty row."))
            continue

        if ck not in groups:
            groups[ck] = CaseDraft(case_key=ck)

        g = groups[ck]
        g.source_rows.append(row_num)

        # Case-level fields: first non-empty wins
        if get(rd, "title") and not g.title:
            g.title = get(rd, "title")
        if get(rd, "description"):
            g.description = g.description or get(rd, "description")
        if get(rd, "preconditions"):
            g.preconditions = g.preconditions or get(rd, "preconditions")

        pr = get(rd, "priority")
        if pr:
            pv = _parse_enum_str(pr, VALID_PRIORITIES, TestCasePriority.medium.value, field_name="priority", row=row_num, errors=errors)
            if pv != "__invalid__":
                g.priority = TestCasePriority(pv)
        cat = get(rd, "category")
        if cat:
            cv = _parse_enum_str(cat, VALID_CATEGORIES, TestCaseCategory.regression.value, field_name="category", row=row_num, errors=errors)
            if cv != "__invalid__":
                g.category = TestCaseCategory(cv)
        st = get(rd, "status")
        if st:
            sv = _parse_enum_str(st, VALID_STATUSES, TestCaseStatus.ready.value, field_name="status", row=row_num, errors=errors)
            if sv != "__invalid__":
                g.status = TestCaseStatus(sv)
        if get(rd, "tags"):
            g.tags = g.tags or get(rd, "tags")
        if get(rd, "requirement_id"):
            rid = _parse_int(get(rd, "requirement_id"), field_name="requirement_id", row=row_num, errors=errors)
            if rid is not None:
                g.requirement_id = g.requirement_id or rid
        if get(rd, "user_story_id"):
            sid = _parse_int(get(rd, "user_story_id"), field_name="user_story_id", row=row_num, errors=errors)
            if sid is not None:
                g.user_story_id = g.user_story_id or sid

        act_raw = get(rd, "action")
        tgt = get(rd, "target") or None
        val = get(rd, "value") or None
        sdesc = get(rd, "step_description") or None
        exp = get(rd, "expected_result") or None
        snum_raw = get(rd, "step_number")

        has_step_signal = bool(act_raw or tgt or val or sdesc or exp or snum_raw)
        if not has_step_signal:
            continue

        action_token = _normalize_action_token(act_raw)
        if not action_token and (tgt or val or sdesc):
            action_token = "custom"
        if not action_token:
            errors.append(
                CsvImportErrorItem(
                    row=row_num,
                    column="action",
                    message="Step fields present but action is missing or invalid; use a valid action or omit all step columns for a no-step row.",
                )
            )
            continue

        try:
            action_enum = TestStepAction(action_token)
        except ValueError:
            errors.append(CsvImportErrorItem(row=row_num, column="action", message=f"Unknown action: {act_raw!r}"))
            continue

        snum: Optional[int] = None
        if snum_raw:
            snum = _parse_int(snum_raw, field_name="step_number", row=row_num, errors=errors)
            if snum is not None and snum < 1:
                errors.append(CsvImportErrorItem(row=row_num, column="step_number", message="step_number must be >= 1"))
                snum = None

        g.steps.append(
            StepDraft(
                step_number=snum,
                action=action_enum,
                target=tgt,
                value=val,
                description=sdesc,
                expected_result=exp,
                source_row=row_num,
            )
        )

    # Finalize titles and step numbers
    for ck, g in list(groups.items()):
        if not g.title:
            g.title = ck
        used: set = set()
        auto = 1
        for st in g.steps:
            if st.step_number is not None:
                if st.step_number in used:
                    errors.append(
                        CsvImportErrorItem(
                            row=st.source_row,
                            column="step_number",
                            message=f"Duplicate step_number {st.step_number} for case_key {ck!r}",
                        )
                    )
                    st.step_number = None
                else:
                    used.add(st.step_number)
        for st in g.steps:
            if st.step_number is None:
                while auto in used:
                    auto += 1
                st.step_number = auto
                used.add(auto)
                auto += 1

    return groups, errors


def validate_groups_non_empty(groups: Dict[str, CaseDraft], errors: List[CsvImportErrorItem]) -> None:
    if not groups:
        errors.append(CsvImportErrorItem(row=0, message="No valid data rows after parsing."))


def collect_case_constraint_violations(
    groups: Dict[str, CaseDraft],
) -> List[Tuple[str, CsvImportErrorItem]]:
    """Return (case_key, issue) for case-level field limits (DB / UX constraints)."""
    out: List[Tuple[str, CsvImportErrorItem]] = []
    for ck, g in groups.items():
        row_hint = min(g.source_rows) if g.source_rows else 0
        if len(ck) > 50:
            out.append(
                (
                    ck,
                    CsvImportErrorItem(
                        row=row_hint,
                        column="case_key",
                        message="case_key must be at most 50 characters (stored as the test case external id).",
                    ),
                )
            )
        title = (g.title or ck or "").strip()
        if len(title) > 500:
            out.append(
                (
                    ck,
                    CsvImportErrorItem(
                        row=row_hint,
                        column="title",
                        message="title exceeds 500 characters.",
                    ),
                )
            )
        if g.tags and len(g.tags.strip()) > 500:
            out.append(
                (
                    ck,
                    CsvImportErrorItem(
                        row=row_hint,
                        column="tags",
                        message="tags exceed 500 characters (comma-separated).",
                    ),
                )
            )
        for st in g.steps:
            if st.target and len(st.target) > 500:
                out.append(
                    (
                        ck,
                        CsvImportErrorItem(
                            row=st.source_row,
                            column="target",
                            message="target exceeds 500 characters.",
                        ),
                    )
                )
    return out


CSV_TEMPLATE_BODY = """case_key,title,description,preconditions,priority,category,status,tags,requirement_id,user_story_id,step_number,action,target,value,step_description,expected_result
LOGIN-001,User can log in,,,high,regression,ready,,,,,,,,,
LOGIN-001,,,,,,,,,,1,navigate,https://app.example.com/login,,,Login page loads
LOGIN-001,,,,,,,,,,2,type,#email,user@example.com,,,
LOGIN-001,,,,,,,,,,3,type,#password,secret,,,
LOGIN-001,,,,,,,,,,4,click,#login-btn,,,,
LOGIN-001,,,,,,,,,,5,assert_visible,#dashboard,,User sees dashboard,Dashboard visible
NO-STEPS-001,Placeholder case with no steps yet,,,medium,draft,draft,,,,,,,,,
"""


def csv_template_text() -> str:
    intro = (
        "# QAstra test case CSV (UTF-8). Remove lines starting with # before uploading in Excel if needed.\n"
        "# case_key: required; max 50 chars; stored as the test case external id (same field as Jira key in the UI).\n"
        "# Same case_key on multiple rows = one test case; merge metadata from the first non-empty cells.\n"
        "# title on first row per case; omit title on step-only rows (falls back to case_key).\n"
        "# Leave all step columns empty for cases with zero steps — valid for placeholders.\n"
        "# Import modes (API): strict = abort whole file on any error; permissive = skip bad cases, import the rest.\n"
        "# priority: critical|high|medium|low  category: smoke|regression|e2e|integration|sanity  status: draft|ready|deprecated\n"
        "# action: navigate|click|type|fill|select|check|uncheck|hover|screenshot|wait|assert_text|assert_visible|assert_url|assert_title|custom\n"
        "\n"
    )
    return intro + CSV_TEMPLATE_BODY
