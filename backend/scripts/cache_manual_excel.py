"""
Parse F2MX manual test case Excel files → JSON cache (run once).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(r"D:\qastra_v2")
CACHE = ROOT / "AmzurQAstra-V2" / "backend" / "scripts" / "cache" / "f2mx_manual_cases.json"
FILES = [
    (ROOT / "F2MX  Sprint 1 Test cases.xlsx", "Sprint 1"),
    (ROOT / "F2MX-Sprint 2 Test Cases.xlsx", "Sprint 2"),
]


def _norm(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip())


def _col_map(columns) -> Dict[str, str]:
    return {str(c).lower().strip(): str(c) for c in columns if isinstance(c, str)}


def _pick(cols: Dict[str, str], *needles: str) -> str | None:
    for n in needles:
        for k, v in cols.items():
            if n in k:
                return v
    return None


def parse_workbook(path: Path, sprint: str) -> Dict[str, Any]:
    xl = pd.ExcelFile(path)
    summary_rows: List[Dict[str, Any]] = []
    sheets: Dict[str, List[Dict[str, str]]] = {}

    if "Summary" in xl.sheet_names:
        sdf = xl.parse("Summary", header=0)
        for _, row in sdf.iterrows():
            story = _norm(row.iloc[0])
            if not story or story.lower() in ("total", "nan", "web user stories", "mobile user stories"):
                continue
            count = row.get("Test Cases Count") or row.get("Test Case Count")
            try:
                tc_count = int(float(count)) if count == count else 0
            except (TypeError, ValueError):
                tc_count = 0
            if tc_count <= 0:
                continue
            pos = row.get("Positive Count") or row.get("Positive")
            neg = row.get("Negative Count") or row.get("Negative")
            summary_rows.append(
                {
                    "sprint": sprint,
                    "story_name": story,
                    "test_case_count": tc_count,
                    "positive": int(float(pos)) if pos == pos else None,
                    "negative": int(float(neg)) if neg == neg else None,
                    "notes": _norm(row.get("Unnamed: 4") or row.get("Dev Comments") or ""),
                }
            )

    for sheet in xl.sheet_names:
        if sheet.lower() == "summary":
            continue
        df = xl.parse(sheet, header=0)
        if df.empty:
            continue
        cols = _col_map(df.columns)
        id_c = _pick(cols, "test case id")
        func_c = _pick(cols, "functionality", "module")
        type_c = _pick(cols, "test case type")
        obj_c = _pick(cols, "test objective", "objective")
        steps_c = _pick(cols, "test executions steps", "steps to execute", "steps")
        exp_c = _pick(cols, "expected result")
        status_c = _pick(cols, "devstatus", "dev status")
        if not obj_c and not steps_c:
            continue

        rows: List[Dict[str, str]] = []
        for _, row in df.iterrows():
            tc_id = _norm(row.get(id_c, "")) if id_c else ""
            objective = _norm(row.get(obj_c, "")) if obj_c else ""
            steps = _norm(row.get(steps_c, "")) if steps_c else ""
            if not tc_id and not objective:
                continue
            if tc_id.lower() in ("test case id", ""):
                continue
            rows.append(
                {
                    "test_id": tc_id,
                    "functionality": _norm(row.get(func_c, "")) if func_c else "",
                    "case_type": _norm(row.get(type_c, "")) if type_c else "",
                    "objective": objective,
                    "steps": steps,
                    "expected": _norm(row.get(exp_c, "")) if exp_c else "",
                    "dev_status": _norm(row.get(status_c, "")) if status_c else "",
                }
            )
        if rows:
            sheets[sheet] = rows

    return {"sprint": sprint, "file": path.name, "summary": summary_rows, "sheets": sheets}


def main() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out: Dict[str, Any] = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "workbooks": []}
    for path, sprint in FILES:
        print(f"Parsing {path.name} ...")
        t0 = time.time()
        wb = parse_workbook(path, sprint)
        tc_total = sum(len(v) for v in wb["sheets"].values())
        summary_total = sum(r["test_case_count"] for r in wb["summary"])
        print(f"  sheets={len(wb['sheets'])} detail_rows={tc_total} summary_total={summary_total} ({time.time()-t0:.1f}s)")
        out["workbooks"].append(wb)

    CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cache written: {CACHE}")


if __name__ == "__main__":
    main()
