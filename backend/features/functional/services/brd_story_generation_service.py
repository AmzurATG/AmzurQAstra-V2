"""
BRD Story Generation Service — BRD text → AI-suggested user stories.

Two-pass LLM pipeline (+ optional Pass 1b UI merge):
  Pass 1: Decompose BRD into functional modules.
  Pass 1b: Merge with UI discovery inventory (when available).
  Pass 2: Expand modules into user stories with full acceptance criteria.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.user_story import UserStory, UserStoryPriority, UserStorySource
from common.llm import get_llm_client
from common.llm.base import Message
from features.functional.core.llm_prompts.brd_story_generation import (
    BRD_DECOMPOSE_PROMPT,
    BRD_STORY_EXPAND_PROMPT,
    BRD_STORY_EXPAND_WITH_UI_PROMPT,
    BRD_UI_MERGE_PROMPT,
)
from features.functional.db.models.requirement import Requirement
from features.functional.schemas.brd_stories import SuggestedStory
from features.functional.services.ui_context_loader import format_inventory_for_prompt, get_latest_inventory

logger = logging.getLogger(__name__)

MAX_BRD_CHARS = 80_000
_VALID_PRIORITIES = {"critical", "high", "medium", "low"}
_VALID_DISCOVERY_SOURCES = {"brd_generated", "ui_discovered", "brd_ui_merged"}


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Extract a JSON array from LLM response, stripping markdown fences if present."""
    raw = text.strip()
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*\])\s*```", raw)
    if m:
        raw = m.group(1)
    else:
        m2 = re.search(r"(\[[\s\S]*\])", raw)
        if m2:
            raw = m2.group(1)
    return json.loads(raw)


class BrdStoryGenerationService:
    """Generates AI user stories from a BRD document (two-pass LLM pipeline)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm_client()

    async def _fetch_requirement(self, project_id: int, requirement_id: int) -> Requirement:
        req = await self.db.get(Requirement, requirement_id)
        if not req or req.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
        if not (req.content or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Requirement has no parsed text. Upload and process a document first.",
            )
        return req

    async def _decompose_modules(self, brd_text: str) -> List[Dict[str, str]]:
        """Pass 1: extract functional modules from BRD text."""
        brd_snippet = brd_text[:MAX_BRD_CHARS]
        response = await asyncio.to_thread(
            self.llm.chat_sync,
            messages=[
                Message(role="system", content=BRD_DECOMPOSE_PROMPT),
                Message(role="user", content=brd_snippet),
            ],
            temperature=0.15,
        )
        return _extract_json_array(response.content or "")

    async def _merge_modules_with_ui(
        self,
        modules: List[Dict[str, str]],
        inventory_text: str,
    ) -> List[Dict[str, str]]:
        """Pass 1b: merge BRD modules with UI discovery inventory."""
        modules_text = json.dumps(modules, indent=2)
        user_msg = f"=== BRD MODULES ===\n{modules_text}\n\n=== UI INVENTORY ===\n{inventory_text}"
        response = await asyncio.to_thread(
            self.llm.chat_sync,
            messages=[
                Message(role="system", content=BRD_UI_MERGE_PROMPT),
                Message(role="user", content=user_msg),
            ],
            temperature=0.15,
        )
        merged = _extract_json_array(response.content or "")
        out: List[Dict[str, str]] = []
        for m in merged:
            out.append(
                {
                    "label": str(m.get("label", "")).strip(),
                    "scope": str(m.get("scope", "")).strip(),
                    "source": str(m.get("source", "both")).strip(),
                }
            )
        return out or modules

    async def _expand_stories(
        self,
        brd_text: str,
        modules: List[Dict[str, str]],
        min_stories: int,
        max_stories: int,
        inventory_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Pass 2: expand modules into user stories with full AC."""
        modules_text = "\n".join(
            f"- {m.get('label', 'Module')} ({m.get('source', 'brd')}): {m.get('scope', '')}"
            for m in modules
        )
        if inventory_text:
            prompt = BRD_STORY_EXPAND_WITH_UI_PROMPT.format(
                min_stories=min_stories, max_stories=max_stories
            )
            user_msg = (
                f"=== BRD ===\n{brd_text[:MAX_BRD_CHARS]}\n\n"
                f"=== MODULES ===\n{modules_text}\n\n"
                f"=== UI INVENTORY ===\n{inventory_text}"
            )
        else:
            prompt = BRD_STORY_EXPAND_PROMPT.format(min_stories=min_stories, max_stories=max_stories)
            user_msg = (
                f"=== BRD ===\n{brd_text[:MAX_BRD_CHARS]}\n\n"
                f"=== MODULES ===\n{modules_text}"
            )
        response = await asyncio.to_thread(
            self.llm.chat_sync,
            messages=[
                Message(role="system", content=prompt),
                Message(role="user", content=user_msg),
            ],
            temperature=0.2,
        )
        return _extract_json_array(response.content or "")

    def _coerce_story(self, raw: Dict[str, Any]) -> Optional[SuggestedStory]:
        """Validate and coerce a raw LLM story dict into a SuggestedStory."""
        title = str(raw.get("title", "")).strip()[:120]
        if not title:
            return None
        priority = str(raw.get("priority", "medium")).strip().lower()
        if priority not in _VALID_PRIORITIES:
            priority = "medium"
        discovery_source = str(raw.get("discovery_source", "brd_generated")).strip().lower()
        if discovery_source not in _VALID_DISCOVERY_SOURCES:
            discovery_source = "brd_generated"
        return SuggestedStory(
            title=title,
            description=str(raw.get("description", "")).strip(),
            acceptance_criteria=str(raw.get("acceptance_criteria", "")).strip(),
            priority=priority,
            module=str(raw.get("module", "")).strip()[:60],
            rationale=str(raw.get("rationale", "")).strip(),
            discovery_source=discovery_source,
        )

    async def generate(
        self,
        project_id: int,
        requirement_id: int,
        max_stories: int = 20,
        include_ui_context: bool = True,
    ) -> Tuple[int, List[SuggestedStory]]:
        """
        Run the pipeline and return (modules_count, stories).
        Stories are NOT persisted; caller decides which to accept.
        """
        req = await self._fetch_requirement(project_id, requirement_id)
        brd_text = req.content or ""

        try:
            modules = await self._decompose_modules(brd_text)
        except Exception as exc:
            logger.exception("BRD decompose failed req_id=%s", requirement_id)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        inventory_text: Optional[str] = None
        if include_ui_context:
            inventory = await get_latest_inventory(self.db, project_id)
            if inventory:
                inventory_text = format_inventory_for_prompt(inventory)
                try:
                    modules = await self._merge_modules_with_ui(modules, inventory_text)
                except Exception as exc:
                    logger.warning("BRD UI merge failed, using BRD modules only: %s", exc)

        min_stories = max(3, len(modules) * 2)

        try:
            raw_stories = await self._expand_stories(
                brd_text, modules, min_stories, max_stories, inventory_text=inventory_text
            )
        except Exception as exc:
            logger.exception("BRD story expand failed req_id=%s", requirement_id)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        stories = [self._coerce_story(r) for r in raw_stories]
        stories = [s for s in stories if s is not None][:max_stories]
        return len(modules), stories

    async def accept_stories(
        self,
        project_id: int,
        suggested: List[SuggestedStory],
        indices: Optional[List[int]] = None,
    ) -> Tuple[int, List[int], List[str]]:
        """
        Persist selected (or all) suggested stories to the user_stories table.

        Returns (created_count, story_ids, errors).
        """
        if indices is not None:
            selected = [(i, suggested[i]) for i in indices if 0 <= i < len(suggested)]
        else:
            selected = list(enumerate(suggested))

        priority_map = {
            "critical": UserStoryPriority.critical,
            "high": UserStoryPriority.high,
            "medium": UserStoryPriority.medium,
            "low": UserStoryPriority.low,
        }

        created_ids: List[int] = []
        errors: List[str] = []

        for idx, story in selected:
            try:
                labels: List[str] = []
                if story.module:
                    labels.append(story.module)
                if story.discovery_source and story.discovery_source != "brd_generated":
                    labels.append(story.discovery_source)
                us = UserStory(
                    project_id=project_id,
                    title=story.title[:500],
                    description=story.description or None,
                    acceptance_criteria=story.acceptance_criteria or None,
                    priority=priority_map.get(story.priority, UserStoryPriority.medium),
                    source=UserStorySource.brd_generated,
                    labels=labels or None,
                )
                self.db.add(us)
                await self.db.flush()
                created_ids.append(us.id)
            except Exception as exc:
                errors.append(f"Index {idx}: {exc}")

        await self.db.commit()
        return len(created_ids), created_ids, errors
