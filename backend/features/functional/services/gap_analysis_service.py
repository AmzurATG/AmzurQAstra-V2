"""
Gap analysis: BRD (requirement) text vs user stories — LLM + PDF report.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.db.models.user_story import UserStory, UserStorySource
from common.llm import get_llm_client
from common.llm.base import Message
from config import settings
from features.functional.db.models.gap_analysis_run import GapAnalysisRun
from features.functional.db.models.requirement import Requirement
from features.functional.core.llm_prompts.gap_analysis import GAP_ANALYSIS_SYSTEM
from features.functional.schemas.gap_analysis import GapAnalysisLlmResult, SuggestedUserStory
from features.functional.services.gap_analysis_pdf import build_gap_analysis_pdf

logger = logging.getLogger(__name__)

MAX_BRD_CHARS = 80_000
MAX_STORIES = 100
MAX_STORY_BODY_CHARS = 2_000


def _extract_json_object(text: str) -> Dict[str, Any]:
    raw = text.strip()
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw)
    if m:
        raw = m.group(1)
    else:
        m2 = re.search(r"(\{[\s\S]*\})", raw)
        if m2:
            raw = m2.group(1)
    return json.loads(raw)


def _truncate(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 20] + "\n...[truncated]"


async def _write_pdf_to_storage(project_id: int, run_id: int, data: bytes) -> str:
    base = Path(settings.STORAGE_LOCAL_PATH).resolve()
    subdir = base / "GapAnalysis" / str(project_id)
    subdir.mkdir(parents=True, exist_ok=True)
    filename = f"{run_id}.pdf"
    full = subdir / filename
    async with aiofiles.open(full, "wb") as f:
        await f.write(data)
    return f"GapAnalysis/{project_id}/{filename}".replace("\\", "/")


async def _read_pdf_bytes(relative_path: str) -> Optional[bytes]:
    base = Path(settings.STORAGE_LOCAL_PATH).resolve()
    norm = relative_path.replace("\\", "/").lstrip("/")
    full = (base / norm).resolve()
    try:
        if not str(full).startswith(str(base)):
            return None
    except ValueError:
        return None
    try:
        async with aiofiles.open(full, "rb") as f:
            return await f.read()
    except OSError:
        return None


async def _unlink_stored_file(relative_path: Optional[str]) -> None:
    if not relative_path:
        return
    base = Path(settings.STORAGE_LOCAL_PATH).resolve()
    norm = relative_path.replace("\\", "/").lstrip("/")
    full = (base / norm).resolve()
    try:
        if not str(full).startswith(str(base)):
            return
    except ValueError:
        return

    def _unlink() -> None:
        try:
            full.unlink(missing_ok=True)
        except OSError:
            pass

    await asyncio.to_thread(_unlink)


class GapAnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_client()

    async def _precheck(
        self, project_id: int, requirement_id: int
    ) -> Tuple[Requirement, int]:
        req = await self.db.get(Requirement, requirement_id)
        if not req or req.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
        content = (req.content or "").strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Requirement has no parsed text. Upload and process a document first.",
            )
        cnt = await self.db.scalar(
            select(func.count()).select_from(UserStory).where(UserStory.project_id == project_id)
        )
        if not cnt or cnt < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No user stories for this project. Import or create user stories before gap analysis.",
            )
        return req, int(cnt)

    def _build_user_message(self, brd: str, stories: List[UserStory], truncated_brd: bool) -> str:
        lines = [
            "=== BRD / REQUIREMENT DOCUMENT ===",
            _truncate(brd, MAX_BRD_CHARS),
        ]
        if truncated_brd:
            lines.append("\n(Note: BRD text was truncated for this analysis.)")
        lines.append("\n=== USER STORIES (backlog) ===")
        for i, s in enumerate(stories[:MAX_STORIES], 1):
            key = s.external_key or f"#{s.id}"
            block = (
                f"\n--- Story {i} [{key}] ---\n"
                f"Title: {s.title}\n"
                f"Description: {_truncate(s.description, MAX_STORY_BODY_CHARS)}\n"
            )
            if s.acceptance_criteria:
                block += f"Acceptance criteria: {_truncate(s.acceptance_criteria, 1000)}\n"
            lines.append(block)
        if len(stories) > MAX_STORIES:
            lines.append(f"\n(Only first {MAX_STORIES} stories included.)")
        return "\n".join(lines)

    async def run_analysis(
        self, project_id: int, requirement_id: int, user_id: int
    ) -> GapAnalysisRun:
        requirement, _story_count = await self._precheck(project_id, requirement_id)

        result = await self.db.execute(
            select(UserStory)
            .where(UserStory.project_id == project_id)
            .order_by(UserStory.id.asc())
            .limit(MAX_STORIES)
        )
        stories = list(result.scalars().all())

        brd_full = requirement.content or ""
        truncated_brd = len(brd_full) > MAX_BRD_CHARS
        user_msg = self._build_user_message(brd_full, stories, truncated_brd)

        llm_messages = [
            Message(role="system", content=GAP_ANALYSIS_SYSTEM),
            Message(role="user", content=user_msg),
        ]

        try:
            response = await asyncio.to_thread(
                self.llm.chat_sync,
                messages=llm_messages,
                temperature=0.15,
            )
            raw_text = response.content or ""
            parsed = _extract_json_object(raw_text)
            validated = GapAnalysisLlmResult.model_validate(parsed)
            result_dict = validated.model_dump()
        except Exception as e:
            logger.exception("Gap analysis LLM/parse failed")
            run = GapAnalysisRun(
                project_id=project_id,
                requirement_id=requirement_id,
                created_by=user_id,
                status="failed",
                error_message=str(e)[:2000],
                result_json=None,
                pdf_path=None,
            )
            self.db.add(run)
            await self.db.commit()
            return await self._get_run_loaded(run.id)

        pdf_bytes: Optional[bytes] = None
        try:
            pdf_bytes = build_gap_analysis_pdf(requirement.title, result_dict)
        except Exception as e:
            logger.exception("Gap analysis PDF render failed")
            warns = result_dict.get("_export_warnings")
            if not isinstance(warns, list):
                warns = []
            else:
                warns = list(warns)
            warns.append(f"PDF could not be generated: {str(e)[:500]}")
            result_dict["_export_warnings"] = warns

        run = GapAnalysisRun(
            project_id=project_id,
            requirement_id=requirement_id,
            created_by=user_id,
            status="completed",
            result_json=result_dict,
            error_message=None,
            pdf_path=None,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)

        if pdf_bytes is not None:
            try:
                rel = await _write_pdf_to_storage(project_id, run.id, pdf_bytes)
                run.pdf_path = rel
                await self.db.commit()
            except Exception as e:
                logger.exception("Gap analysis PDF write failed")
                warns = result_dict.get("_export_warnings")
                if not isinstance(warns, list):
                    warns = []
                else:
                    warns = list(warns)
                warns.append(f"PDF could not be saved: {e}")
                result_dict["_export_warnings"] = warns
                run.result_json = result_dict
                run.pdf_path = None
                await self.db.commit()
        else:
            await self.db.commit()

        return await self._get_run_loaded(run.id)

    async def _get_run_loaded(self, run_id: int) -> GapAnalysisRun:
        out = await self.db.execute(
            select(GapAnalysisRun)
            .options(selectinload(GapAnalysisRun.requirement))
            .where(GapAnalysisRun.id == run_id)
        )
        return out.scalar_one()

    async def list_runs(
        self,
        project_id: int,
        offset: int,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        count_q = await self.db.scalar(
            select(func.count()).select_from(GapAnalysisRun).where(GapAnalysisRun.project_id == project_id)
        )
        total = int(count_q or 0)
        q = (
            select(GapAnalysisRun)
            .options(selectinload(GapAnalysisRun.requirement))
            .where(GapAnalysisRun.project_id == project_id)
            .order_by(GapAnalysisRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(q)
        rows = res.scalars().all()
        items = []
        for r in rows:
            req = r.requirement
            items.append(
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "requirement_id": r.requirement_id,
                    "created_by": r.created_by,
                    "status": r.status,
                    "result_json": r.result_json,
                    "error_message": r.error_message,
                    "pdf_path": r.pdf_path,
                    "requirement_title": req.title if req else None,
                    "requirement_file_name": req.file_name if req else None,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
            )
        return items, total

    async def get_run(self, run_id: int, project_id: int) -> Optional[GapAnalysisRun]:
        res = await self.db.execute(
            select(GapAnalysisRun)
            .options(selectinload(GapAnalysisRun.requirement))
            .where(GapAnalysisRun.id == run_id, GapAnalysisRun.project_id == project_id)
        )
        return res.scalar_one_or_none()

    async def get_pdf_bytes(self, run_id: int, project_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Return PDF bytes for a gap analysis run.

        Reads from ``pdf_path`` when the file exists. For legacy rows (no path,
        or file removed from disk) but ``status=completed`` and ``result_json``
        present, rebuilds the PDF from stored JSON — same renderer used at
        analysis time — and best-effort writes it back so future requests hit
        disk.
        """
        run = await self.get_run(run_id, project_id)
        if not run:
            return None, None

        filename = "gap-analysis-report.pdf"
        if run.requirement and run.requirement.file_name:
            base = run.requirement.file_name.rsplit(".", 1)[0]
            filename = f"{base}-gap-analysis.pdf"

        if run.pdf_path:
            data = await _read_pdf_bytes(run.pdf_path)
            if data:
                return data, filename

        if run.status != "completed" or not run.result_json:
            return None, None

        try:
            req_title = (run.requirement.title if run.requirement else None) or "Requirement"
            pdf_bytes = build_gap_analysis_pdf(req_title, run.result_json)
        except Exception:
            logger.exception("Gap analysis PDF regeneration failed run_id=%s", run_id)
            return None, None

        if not pdf_bytes:
            return None, None

        try:
            rel = await _write_pdf_to_storage(project_id, run.id, pdf_bytes)
            run.pdf_path = rel
            await self.db.commit()
        except Exception as e:
            logger.warning(
                "Could not persist regenerated gap analysis PDF run_id=%s: %s",
                run_id,
                e,
            )
            await self.db.rollback()

        return pdf_bytes, filename

    async def delete_run(self, run_id: int, project_id: int) -> bool:
        run = await self.get_run(run_id, project_id)
        if not run:
            return False
        path = run.pdf_path
        await self.db.delete(run)
        await self.db.commit()
        await _unlink_stored_file(path)
        return True

    async def accept_suggestions(
        self,
        run_id: int,
        project_id: int,
        indices: List[int],
    ) -> Tuple[int, List[str]]:
        run = await self.get_run(run_id, project_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        if run.status != "completed" or not run.result_json:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Run has no completed result to accept stories from.",
            )
        suggested = run.result_json.get("suggested_user_stories") or []
        if not isinstance(suggested, list):
            suggested = []

        created = 0
        errors: List[str] = []
        for idx in indices:
            if idx < 0 or idx >= len(suggested):
                errors.append(f"Invalid index {idx}")
                continue
            item = suggested[idx]
            try:
                su = SuggestedUserStory.model_validate(item)
            except Exception as e:
                errors.append(f"Index {idx}: {e}")
                continue
            story = UserStory(
                project_id=project_id,
                title=su.title[:500],
                description=su.description or None,
                acceptance_criteria=su.acceptance_criteria or None,
                source=UserStorySource.manual,
            )
            self.db.add(story)
            created += 1

        await self.db.commit()
        return created, errors
