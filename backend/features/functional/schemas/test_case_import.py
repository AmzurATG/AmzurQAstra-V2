"""Schemas for bulk CSV import of test cases + steps."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CsvImportErrorItem(BaseModel):
    """One validation issue tied to a source row (1-based, including header as row 1)."""

    row: int
    column: Optional[str] = None
    message: str


class TestCaseCsvImportResponse(BaseModel):
    """Result of CSV import or dry-run."""

    dry_run: bool = False
    import_mode: str = Field(description="strict | permissive")
    created_cases: int = 0
    created_steps: int = 0
    skipped_case_groups: int = 0
    errors: List[CsvImportErrorItem] = Field(default_factory=list)
    warnings: List[CsvImportErrorItem] = Field(default_factory=list)
    message: str = ""
