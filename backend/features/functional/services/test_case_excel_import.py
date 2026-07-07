"""
Parse Excel workbooks into CaseDraft groups for import into QAstra.

Mirrors the structure of test_case_csv_import.py — stateless parse functions
that produce CaseDraft / StepDraft objects; persistence is handled by
TestCaseService.import_test_cases_from_excel.

Field mapping from Excel → CaseDraft:
  test_id          → case_key  (prefixed with sprint_prefix, max 50 chars)
  objective        → title (max 500 chars)
  objective+steps  → description
  steps (prose)    → list of StepDraft(action=custom) — split on "N. " numbering
  expected         → last step's expected_result
  case_type        → tags ("positive" / "negative")
  functionality    → additional tag
  dev_status       → tag "dev:pass" / "dev:fail"
  sheet_name       → user_story_id (via story_id_map fuzzy match)
"""
from __future__ import annotations

import io
import re
import logging
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional, Tuple

from features.functional.db.models.test_case import (
    TestCaseCategory,
    TestCasePriority,
    TestCaseStatus,
)
from features.functional.db.models.test_step import TestStepAction
from features.functional.schemas.test_case_import import CsvImportErrorItem
from features.functional.services.test_case_csv_import import CaseDraft, StepDraft

logger = logging.getLogger(__name__)

MAX_EXCEL_BYTES = 20 * 1024 * 1024  # 20 MiB
MAX_CASE_KEY_LEN = 50
MAX_TITLE_LEN = 500

# Prose step numbering patterns: "1. " / "1) " / "Step 1:" / "- "
_STEP_SPLIT_RE = re.compile(
    r"(?:^|\n)\s*(?:step\s*\d+\s*[:\-]|\d+[.)]\s+|[-•]\s+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Low-level helpers (also shared with scripts/cache_manual_excel.py logic)
# ---------------------------------------------------------------------------

def _norm(v: Any) -> str:
    """Normalise a cell value to a stripped string; handle NaN / None."""
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "n/a", ""):
        return ""
    return " ".join(s.split())  # collapse internal whitespace


def _col_map(columns: Any) -> Dict[str, str]:
    """Return {lowercase_header: original_header} for fuzzy column lookup."""
    return {str(c).strip().lower(): str(c) for c in columns}


def _pick(cols: Dict[str, str], *needles: str) -> Optional[str]:
    """Return the first column whose lowercased name contains any needle."""
    for lc, orig in cols.items():
        for needle in needles:
            if needle in lc:
                return orig
    return None


def _make_case_key(test_id: str, sprint_prefix: str) -> str:
    raw = f"{sprint_prefix}{test_id}" if sprint_prefix else test_id
    # Truncate to MAX_CASE_KEY_LEN; replace spaces with underscores
    return raw.replace(" ", "_")[:MAX_CASE_KEY_LEN]


def _parse_prose_steps(prose: str) -> List[str]:
    """Split numbered prose text into individual step strings."""
    if not prose:
        return []
    parts = _STEP_SPLIT_RE.split(prose)
    result = [p.strip() for p in parts if p.strip()]
    if not result:
        result = [prose.strip()]
    return result


def _build_step_drafts(steps_prose: str, expected: str) -> List[StepDraft]:
    """Convert prose step text into a list of StepDraft objects."""
    lines = _parse_prose_steps(steps_prose)
    if not lines:
        if expected:
            return [StepDraft(
                step_number=1,
                action=TestStepAction.custom,
                description="Execute test case",
                expected_result=expected or None,
            )]
        return []

    drafts: List[StepDraft] = []
    for i, line in enumerate(lines, start=1):
        exp = expected if i == len(lines) else None
        drafts.append(StepDraft(
            step_number=i,
            action=TestStepAction.custom,
            description=line[:500] or None,
            expected_result=exp[:500] if exp else None,
        ))
    return drafts


def _build_tags(*parts: str) -> Optional[str]:
    """Merge non-empty tag strings into a comma-separated tag value."""
    tags = [p.strip().lower() for p in parts if p.strip()]
    return ", ".join(tags) if tags else None


# ---------------------------------------------------------------------------
# Sheet → story_name mapping helpers
# ---------------------------------------------------------------------------

def match_sheet_to_story(
    sheet_name: str,
    story_names: List[str],
) -> Optional[str]:
    """Return the best-matching story_name for a truncated sheet_name.

    Excel truncates sheet names to 31 chars.  We use prefix matching first,
    then token overlap as fallback.
    """
    if not story_names:
        return None

    sheet_lc = sheet_name.lower().strip()

    # 1. Prefix match (sheet name is truncated story name)
    for sn in story_names:
        if sn.lower().startswith(sheet_lc) or sheet_lc.startswith(sn.lower()[:31]):
            return sn

    # 2. Token overlap
    sheet_tokens = set(sheet_lc.split())
    best_sn = None
    best_score = 0.0
    for sn in story_names:
        sn_tokens = set(sn.lower().split())
        if not sn_tokens:
            continue
        overlap = len(sheet_tokens & sn_tokens) / len(sheet_tokens | sn_tokens)
        if overlap > best_score:
            best_score = overlap
            best_sn = sn

    if best_score >= 0.3:
        return best_sn
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decode_excel_bytes(
    data: bytes,
) -> Tuple[Any, List[CsvImportErrorItem]]:
    """Parse raw Excel bytes into a pandas ExcelFile.

    Args:
        data: Raw .xlsx/.xls bytes from an uploaded file.

    Returns:
        (xl, errors) where xl is a pd.ExcelFile (or None on failure) and
        errors is a list of CsvImportErrorItem describing decoding problems.
    """
    errors: List[CsvImportErrorItem] = []
    if len(data) > MAX_EXCEL_BYTES:
        errors.append(CsvImportErrorItem(
            row=0, message=f"File too large: {len(data) // (1024*1024)} MiB (max {MAX_EXCEL_BYTES // (1024*1024)} MiB)"
        ))
        return None, errors

    try:
        import pandas as pd  # type: ignore
        xl = pd.ExcelFile(io.BytesIO(data))
    except Exception as exc:
        errors.append(CsvImportErrorItem(row=0, message=f"Cannot open workbook: {exc}"))
        return None, errors

    return xl, errors


def parse_workbook_to_groups(
    xl: Any,
    *,
    story_id_map: Dict[str, int],
    sprint_prefix: str = "",
    import_mode: str = "permissive",
) -> Tuple[Dict[str, CaseDraft], List[CsvImportErrorItem]]:
    """Convert all detail sheets in an Excel workbook to CaseDraft groups.

    Args:
        xl:            pandas ExcelFile opened from raw bytes.
        story_id_map:  Mapping of Excel story_name → user_story_id in the DB.
                       Built by excel_story_mapper.build_story_id_map().
        sprint_prefix: String prepended to case_key (e.g. "S1-") to avoid
                       cross-sprint key collisions.
        import_mode:   "strict" aborts on unmapped story; "permissive" skips.

    Returns:
        (groups, errors) where groups is {case_key: CaseDraft} and errors
        is a list of CsvImportErrorItem for issues found during parsing.
    """
    import pandas as pd  # type: ignore

    groups: Dict[str, CaseDraft] = {}
    errors: List[CsvImportErrorItem] = []
    story_names = list(story_id_map.keys())

    for sheet_name in xl.sheet_names:
        if sheet_name.lower() == "summary":
            continue  # skip roll-up tab

        try:
            df = xl.parse(sheet_name, header=0)
        except Exception as exc:
            errors.append(CsvImportErrorItem(
                row=0,
                column=sheet_name,
                message=f"Failed to parse sheet '{sheet_name}': {exc}",
            ))
            continue

        if df.empty:
            continue

        cols = _col_map(df.columns)

        # Fuzzy column lookup
        col_id = _pick(cols, "test case id", "test_case_id", "id", "tc_id")
        col_obj = _pick(cols, "test objective", "objective")
        col_steps = _pick(cols, "test executions steps", "steps to execute", "steps")
        col_expected = _pick(cols, "expected result", "expected")
        col_func = _pick(cols, "functionality", "module", "feature")
        col_type = _pick(cols, "test case type", "case type", "type")
        col_status = _pick(cols, "devstatus", "dev status", "status")

        if col_obj is None and col_steps is None:
            logger.debug("[ExcelImport] Skipping sheet '%s': no objective or steps column.", sheet_name)
            continue

        # Resolve story_id for this sheet
        matched_story = match_sheet_to_story(sheet_name, story_names)
        story_id: Optional[int] = story_id_map.get(matched_story) if matched_story else None
        if story_id is None and import_mode == "strict":
            errors.append(CsvImportErrorItem(
                row=0,
                column=sheet_name,
                message=(
                    f"Sheet '{sheet_name}' could not be mapped to a project story. "
                    "Add the story to QAstra first, or use import_mode=permissive."
                ),
            ))
            continue

        for row_idx, row in df.iterrows():
            row_num = int(row_idx) + 2  # 1-based with header as row 1

            test_id = _norm(row[col_id]) if col_id else ""
            objective = _norm(row[col_obj]) if col_obj else ""
            steps_prose = _norm(row[col_steps]) if col_steps else ""
            expected = _norm(row[col_expected]) if col_expected else ""
            functionality = _norm(row[col_func]) if col_func else ""
            case_type = _norm(row[col_type]) if col_type else ""
            dev_status_raw = _norm(row[col_status]) if col_status else ""

            # Skip blank rows
            if not test_id and not objective:
                continue
            # Skip rows that repeat the header labels
            if test_id.lower() in ("test case id", "id", "tc_id"):
                continue

            if not test_id:
                test_id = f"ROW_{row_num}"

            case_key = _make_case_key(test_id, sprint_prefix)
            title = (objective or test_id)[:MAX_TITLE_LEN]
            description_parts = [p for p in (objective, steps_prose) if p]
            description = "\n\n".join(description_parts)[:2000] or None

            dev_tag = ""
            if dev_status_raw:
                norm_ds = dev_status_raw.lower()
                if "pass" in norm_ds:
                    dev_tag = "dev:pass"
                elif "fail" in norm_ds:
                    dev_tag = "dev:fail"
                else:
                    dev_tag = f"dev:{norm_ds[:20]}"

            tags = _build_tags(case_type, functionality, dev_tag)

            step_drafts = _build_step_drafts(steps_prose, expected)

            if case_key in groups:
                # Duplicate test_id within same workbook — append a suffix
                suffix = 1
                while f"{case_key}_{suffix}" in groups:
                    suffix += 1
                case_key = f"{case_key}_{suffix}"[:MAX_CASE_KEY_LEN]
                errors.append(CsvImportErrorItem(
                    row=row_num,
                    column="test_id",
                    message=f"Duplicate test_id renamed to {case_key!r}",
                ))

            groups[case_key] = CaseDraft(
                case_key=case_key,
                title=title,
                description=description,
                preconditions=None,
                priority=TestCasePriority.medium,
                category=TestCaseCategory.regression,
                status=TestCaseStatus.draft,
                tags=tags,
                requirement_id=None,
                user_story_id=story_id,
                steps=step_drafts,
                source_rows=[row_num],
            )

    return groups, errors
