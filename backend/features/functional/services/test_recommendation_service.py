"""
Test recommendations: domain playbook from YAML.
Domain is chosen by LLM from BRD + user story intent (default), with keyword scoring as
fallback if the LLM fails; optional keyword-first mode for offline use.
Each run persists result JSON, PDF path, and user story snapshot.
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

from common.db.models.user_story import UserStory
from common.llm import get_llm_client
from common.llm.base import Message
from config import settings
from features.functional.core.llm_prompts.test_recommendation_domain import (
    build_test_recommendation_domain_system_message,
)
from features.functional.db.models.gap_analysis_run import GapAnalysisRun
from features.functional.db.models.requirement import Requirement
from features.functional.db.models.test_recommendation_run import TestRecommendationRun
from features.functional.schemas.test_recommendation import LlmDomainClassificationResult
from features.functional.services.recommendation.domain_classifier import (
    classify_domains_keyword,
    strategies_for_domain,
)
from features.functional.services.recommendation.domain_config import (
    domains_catalog_for_prompt,
    load_domain_test_mapping,
)
from features.functional.services.test_recommendation_pdf import build_test_recommendation_pdf

logger = logging.getLogger(__name__)

MAX_BRD_CHARS = 80_000
MAX_STORIES = 100
MAX_STORY_BODY_CHARS = 2_000
GENERAL_DOMAIN_ID = "general"


def _truncate(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 20] + "\n...[truncated]"


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


def _build_corpus(brd: str, stories: List[UserStory], *, truncated_note: List[str]) -> str:
    lines = [
        "=== BRD / REQUIREMENT DOCUMENT ===",
        _truncate(brd, MAX_BRD_CHARS),
    ]
    if len(brd or "") > MAX_BRD_CHARS:
        truncated_note.append("BRD text was truncated for this run.")
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
        truncated_note.append(f"Only first {MAX_STORIES} user stories were included.")
    return "\n".join(lines)


async def _write_pdf_to_storage(project_id: int, run_id: int, data: bytes) -> str:
    base = Path(settings.STORAGE_LOCAL_PATH).resolve()
    subdir = base / "TestRecommendations" / str(project_id)
    subdir.mkdir(parents=True, exist_ok=True)
    filename = f"{run_id}.pdf"
    full = subdir / filename
    async with aiofiles.open(full, "wb") as f:
        await f.write(data)
    return f"TestRecommendations/{project_id}/{filename}".replace("\\", "/")


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


class TestRecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_client()

    async def _precheck(self, project_id: int, requirement_id: int) -> Requirement:
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
                detail="No user stories for this project. Import or create user stories before test recommendations.",
            )
        return req

    async def _gap_alignment_warnings(self, requirement_id: int) -> List[str]:
        warnings: List[str] = []
        res = await self.db.execute(
            select(GapAnalysisRun)
            .where(
                GapAnalysisRun.requirement_id == requirement_id,
                GapAnalysisRun.status == "completed",
            )
            .order_by(GapAnalysisRun.created_at.desc())
            .limit(1)
        )
        run = res.scalar_one_or_none()
        if not run or not run.result_json:
            return warnings
        gaps = run.result_json.get("gaps") or []
        if not isinstance(gaps, list):
            return warnings
        bad = 0
        for g in gaps:
            if not isinstance(g, dict):
                continue
            t = str(g.get("type") or "")
            if t in ("missing_in_brd", "inconsistency"):
                bad += 1
        if bad > 0:
            warnings.append(
                f"The latest gap analysis for this requirement reported {bad} item(s) of type "
                "missing_in_brd or inconsistency between the BRD and backlog. Review alignment before relying on recommendations."
            )
        return warnings

    async def _llm_classify_domain(
        self, corpus_for_llm: str, allowed_ids: List[str], domains_catalog: List[tuple[str, str]]
    ) -> LlmDomainClassificationResult:
        system = build_test_recommendation_domain_system_message(domains_catalog)
        messages = [
            Message(role="system", content=system),
            Message(
                role="user",
                content=(
                    "Infer product intent and classify the domain using the BRD and user stories below.\n\n"
                    + corpus_for_llm
                ),
            ),
        ]
        response = await asyncio.to_thread(
            self.llm.chat_sync,
            messages=messages,
            temperature=0.15,
        )
        raw = response.content or ""
        parsed = _extract_json_object(raw)
        llm = LlmDomainClassificationResult.model_validate(parsed)
        if llm.domain_id not in allowed_ids:
            raise ValueError(f"Invalid domain_id from LLM: {llm.domain_id}")
        return llm

    async def run_recommendation(
        self, project_id: int, requirement_id: int, user_id: int
    ) -> TestRecommendationRun:
        try:
            return await self._run_recommendation_core(project_id, requirement_id, user_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Test recommendation run failed")
            await self.db.rollback()
            run = TestRecommendationRun(
                project_id=project_id,
                requirement_id=requirement_id,
                created_by=user_id,
                status="failed",
                result_json=None,
                error_message=str(e)[:2000],
                pdf_path=None,
            )
            self.db.add(run)
            await self.db.commit()
            return await self._get_run_loaded(run.id)

    async def _run_recommendation_core(
        self, project_id: int, requirement_id: int, user_id: int
    ) -> TestRecommendationRun:
        requirement = await self._precheck(project_id, requirement_id)

        stories_total = await self.db.scalar(
            select(func.count()).select_from(UserStory).where(UserStory.project_id == project_id)
        )
        stories_total = int(stories_total or 0)

        result = await self.db.execute(
            select(UserStory)
            .where(UserStory.project_id == project_id)
            .order_by(UserStory.id.asc())
            .limit(MAX_STORIES)
        )
        stories = list(result.scalars().all())

        story_snapshot = [
            {
                "id": s.id,
                "external_key": s.external_key,
                "title": (s.title or "")[:500],
            }
            for s in stories
        ]

        mapping = load_domain_test_mapping()
        truncated_notes: List[str] = []
        brd_full = requirement.content or ""
        corpus = _build_corpus(brd_full, stories, truncated_note=truncated_notes)

        local = classify_domains_keyword(corpus, mapping, general_domain_id=GENERAL_DOMAIN_ID)
        allowed_ids = [d.id for d in mapping.domains]
        domains_catalog = domains_catalog_for_prompt(mapping)

        chosen_domain: str
        chosen_label: str
        chosen_confidence: float
        source: str
        llm_payload: Optional[Dict[str, Any]] = None
        intent_summary = ""

        capped_corpus = _truncate(corpus, settings.TEST_RECOMMENDATION_LLM_MAX_CORPUS_CHARS)
        use_llm_primary = bool(settings.TEST_RECOMMENDATION_USE_LLM_FOR_DOMAIN)

        if use_llm_primary:
            try:
                llm_result = await self._llm_classify_domain(capped_corpus, allowed_ids, domains_catalog)
                chosen_domain = llm_result.domain_id
                rec = next((d for d in mapping.domains if d.id == chosen_domain), None)
                chosen_label = rec.label if rec else chosen_domain
                chosen_confidence = float(llm_result.confidence)
                source = "llm"
                intent_summary = (llm_result.intent_summary or "").strip()
                llm_payload = {
                    "domain_id": llm_result.domain_id,
                    "confidence": llm_result.confidence,
                    "rationale": llm_result.rationale,
                    "intent_summary": intent_summary,
                }
            except Exception as e:
                logger.exception("Test recommendation LLM domain classification failed")
                llm_payload = {"error": str(e)[:500]}
                chosen_domain = local.domain_id
                chosen_label = local.label
                chosen_confidence = float(local.confidence)
                source = "keyword_fallback"
                truncated_notes.append(
                    "Domain was selected using keyword matching because LLM classification failed. "
                    "Verify LLM API keys and connectivity."
                )
        else:
            chosen_domain = local.domain_id
            chosen_label = local.label
            chosen_confidence = float(local.confidence)
            source = "keyword"
            threshold = float(settings.TEST_RECOMMENDATION_DOMAIN_CONFIDENCE_THRESHOLD)
            if settings.TEST_RECOMMENDATION_LLM_FALLBACK_ENABLED and local.confidence < threshold:
                try:
                    llm_result = await self._llm_classify_domain(capped_corpus, allowed_ids, domains_catalog)
                    intent_summary = (llm_result.intent_summary or "").strip()
                    llm_payload = {
                        "domain_id": llm_result.domain_id,
                        "confidence": llm_result.confidence,
                        "rationale": llm_result.rationale,
                        "intent_summary": intent_summary,
                    }
                    if llm_result.confidence > local.confidence:
                        chosen_domain = llm_result.domain_id
                        rec = next((d for d in mapping.domains if d.id == chosen_domain), None)
                        chosen_label = rec.label if rec else chosen_domain
                        chosen_confidence = float(llm_result.confidence)
                        source = "llm"
                except Exception as e:
                    logger.exception("Test recommendation LLM domain fallback failed")
                    llm_payload = {"error": str(e)[:500]}

        std, recs = strategies_for_domain(chosen_domain, mapping, general_domain_id=GENERAL_DOMAIN_ID)

        warnings = await self._gap_alignment_warnings(requirement_id)
        warnings.extend(truncated_notes)

        pct = float(chosen_confidence) * 100.0 if chosen_confidence is not None else 0.0
        base_tail = (
            f"This run used {len(story_snapshot)} user stor{'y' if len(story_snapshot) == 1 else 'ies'} "
            f"(up to {MAX_STORIES} by ascending id) and the selected requirement text."
        )
        report_summary = (
            f"Detected domain “{chosen_label}” ({pct:.0f}% confidence; source: {source}). {base_tail}"
        )

        input_snapshot: Dict[str, Any] = {
            "run_kind": "test_recommendations",
            "requirement_id": requirement_id,
            "project_id": project_id,
            "user_stories_included": story_snapshot,
            "user_stories_total_in_project": stories_total,
            "max_stories_cap": MAX_STORIES,
            "ordering": "user_stories.id ascending",
        }

        result_dict: Dict[str, Any] = {
            "domain_id": chosen_domain,
            "domain_label": chosen_label,
            "confidence": chosen_confidence,
            "source": source,
            "report_summary": report_summary,
            "input_snapshot": input_snapshot,
            "local_classification": {
                "domain_id": local.domain_id,
                "confidence": local.confidence,
                "label": local.label,
                "per_domain_scores": local.per_domain_scores,
                "evidence": local.evidence,
                "score_breakdown": local.score_breakdown,
            },
            "llm_fallback": llm_payload,
            "standard_tests": std,
            "recommended_tests": recs,
            "warnings": warnings,
        }
        if intent_summary:
            result_dict["intent_summary"] = intent_summary

        run = TestRecommendationRun(
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

        pdf_bytes: Optional[bytes] = None
        try:
            req_title = requirement.title or requirement.file_name or "Requirement"
            pdf_bytes = build_test_recommendation_pdf(req_title, result_dict)
        except Exception as e:
            logger.exception("Test recommendation PDF render failed")
            warns = result_dict.get("_export_warnings")
            if not isinstance(warns, list):
                warns = []
            else:
                warns = list(warns)
            warns.append(f"PDF could not be generated: {str(e)[:500]}")
            result_dict["_export_warnings"] = warns
            run.result_json = result_dict

        if pdf_bytes is not None:
            try:
                rel = await _write_pdf_to_storage(project_id, run.id, pdf_bytes)
                run.pdf_path = rel
                await self.db.commit()
            except Exception as e:
                logger.exception("Test recommendation PDF write failed")
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

    async def _get_run_loaded(self, run_id: int) -> TestRecommendationRun:
        out = await self.db.execute(
            select(TestRecommendationRun)
            .options(selectinload(TestRecommendationRun.requirement))
            .where(TestRecommendationRun.id == run_id)
        )
        return out.scalar_one()

    async def list_runs(
        self,
        project_id: int,
        offset: int,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        count_q = await self.db.scalar(
            select(func.count())
            .select_from(TestRecommendationRun)
            .where(TestRecommendationRun.project_id == project_id)
        )
        total = int(count_q or 0)
        q = (
            select(TestRecommendationRun)
            .options(selectinload(TestRecommendationRun.requirement))
            .where(TestRecommendationRun.project_id == project_id)
            .order_by(TestRecommendationRun.created_at.desc())
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

    async def get_run(self, run_id: int, project_id: int) -> Optional[TestRecommendationRun]:
        res = await self.db.execute(
            select(TestRecommendationRun)
            .options(selectinload(TestRecommendationRun.requirement))
            .where(TestRecommendationRun.id == run_id, TestRecommendationRun.project_id == project_id)
        )
        return res.scalar_one_or_none()

    async def get_pdf_bytes(self, run_id: int, project_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        run = await self.get_run(run_id, project_id)
        if not run:
            return None, None

        filename = "test-recommendations-report.pdf"
        if run.requirement and run.requirement.file_name:
            base = run.requirement.file_name.rsplit(".", 1)[0]
            filename = f"{base}-test-recommendations.pdf"

        if run.pdf_path:
            data = await _read_pdf_bytes(run.pdf_path)
            if data:
                return data, filename

        if run.status != "completed" or not run.result_json:
            return None, None

        try:
            req_title = (run.requirement.title if run.requirement else None) or "Requirement"
            pdf_bytes = build_test_recommendation_pdf(req_title, run.result_json)
        except Exception:
            logger.exception("Test recommendation PDF regeneration failed run_id=%s", run_id)
            return None, None

        if not pdf_bytes:
            return None, None

        try:
            rel = await _write_pdf_to_storage(project_id, run.id, pdf_bytes)
            run.pdf_path = rel
            await self.db.commit()
        except Exception as e:
            logger.warning(
                "Could not persist regenerated test recommendation PDF run_id=%s: %s",
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
