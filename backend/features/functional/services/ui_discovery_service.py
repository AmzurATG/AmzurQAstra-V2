"""
UI Discovery Service — orchestrates discovery agent runs and persists inventory.
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.project import Project
from common.utils.logger import logger
from features.functional.core.browser.ui_discovery_agent import (
    UiDiscoveryAgent,
    clear_discovery_progress,
    get_discovery_progress,
)
from features.functional.core.llm_prompts.ui_discovery import UI_DISCOVERY_REPAIR_PROMPT
from features.functional.db.models.ui_discovery_run import UiDiscoveryRun, UiDiscoveryRunStatus
from features.functional.schemas.ui_discovery import (
    UiDiscoveryLatestResponse,
    UiDiscoveryStartRequest,
    UiDiscoveryStartResponse,
    UiDiscoveryStatusResponse,
    UiInventory,
)
from features.functional.utils.app_reachability import verify_app_url_reachable

STALE_DAYS = 7


class UiDiscoveryService:
    """Manages UI discovery run lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._agent = UiDiscoveryAgent()

    async def start_discovery(self, request: UiDiscoveryStartRequest) -> UiDiscoveryStartResponse:
        run_id = str(uuid.uuid4())
        record = UiDiscoveryRun(
            project_id=request.project_id,
            run_id=run_id,
            status=UiDiscoveryRunStatus.pending,
            platform="web",
            actor_role=request.actor_role,
            app_url=request.app_url,
            source_integrity_run_id=request.source_integrity_run_id,
            started_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.commit()

        username = request.credentials.username if request.credentials else None
        password = request.credentials.password if request.credentials else None

        asyncio.create_task(
            self._run_and_persist(
                run_id=run_id,
                project_id=request.project_id,
                app_url=request.app_url,
                actor_role=request.actor_role,
                username=username,
                password=password,
                use_google=request.use_google_signin,
                skip_reachability=request.skip_reachability_check,
            )
        )
        return UiDiscoveryStartResponse(run_id=run_id, status="pending")

    async def _persist_live_progress(self, run_id: str, payload: Dict[str, Any]) -> None:
        from common.db.database import async_session_maker

        safe = {
            "status": payload.get("status"),
            "percentage": int(payload.get("percentage") or 0),
            "current_step": payload.get("current_step"),
            "screenshots": list(payload.get("screenshots") or []),
            "pages_discovered": int(payload.get("pages_discovered") or 0),
            "partial_inventory": payload.get("inventory"),
        }
        try:
            async with async_session_maker() as db:
                row = await db.execute(select(UiDiscoveryRun).where(UiDiscoveryRun.run_id == run_id))
                record = row.scalar_one_or_none()
                if not record:
                    return
                if safe.get("status") == "running":
                    record.status = UiDiscoveryRunStatus.running
                record.live_progress = safe
                await db.commit()
        except Exception as exc:
            logger.warning("[UiDiscovery] live_progress flush failed run_id=%s: %s", run_id, exc)

    async def _repair_inventory(self, raw_text: str) -> Optional[UiInventory]:
        from common.llm import get_llm_client
        from common.llm.base import Message

        llm = get_llm_client()
        prompt = UI_DISCOVERY_REPAIR_PROMPT.format(raw_text=raw_text[:12000])
        try:
            response = await asyncio.to_thread(
                llm.chat_sync,
                messages=[Message(role="user", content=prompt)],
                temperature=0.0,
            )
            text = (response.content or "").strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            return UiInventory.model_validate(data)
        except Exception as exc:
            logger.warning("[UiDiscovery] inventory repair failed: %s", exc)
            return None

    async def _run_and_persist(
        self,
        run_id: str,
        project_id: int,
        app_url: str,
        actor_role: str,
        username: Optional[str],
        password: Optional[str],
        use_google: bool,
        skip_reachability: bool,
    ) -> None:
        from common.db.database import async_session_maker

        try:
            if not skip_reachability:
                ok, err = await verify_app_url_reachable(app_url)
                if not ok:
                    async with async_session_maker() as db:
                        row = await db.execute(select(UiDiscoveryRun).where(UiDiscoveryRun.run_id == run_id))
                        record = row.scalar_one_or_none()
                        if record:
                            record.status = UiDiscoveryRunStatus.error
                            record.error_message = err
                            record.completed_at = datetime.utcnow()
                            await db.commit()
                    clear_discovery_progress(run_id)
                    return

            result = await self._agent.run(
                run_id=run_id,
                app_url=app_url,
                actor_role=actor_role,
                username=username,
                password=password,
                use_google_signin=use_google,
                live_progress_writer=self._persist_live_progress,
            )

            inventory_data = result.get("inventory")
            inventory: Optional[UiInventory] = None
            if inventory_data:
                inventory = UiInventory.model_validate(inventory_data)
            elif result.get("raw_output"):
                inventory = await self._repair_inventory(result["raw_output"])

            async with async_session_maker() as db:
                row = await db.execute(select(UiDiscoveryRun).where(UiDiscoveryRun.run_id == run_id))
                record = row.scalar_one_or_none()
                if not record:
                    return

                record.duration_ms = result.get("duration_ms")
                record.screenshots = list(result.get("screenshots") or [])
                record.completed_at = datetime.utcnow()
                record.live_progress = None

                if inventory:
                    record.status = UiDiscoveryRunStatus.completed
                    record.inventory_json = inventory.model_dump()
                    record.summary = result.get("summary") or f"Discovered {len(inventory.pages)} pages."
                    record.error_message = None

                    proj = await db.get(Project, project_id)
                    if proj:
                        proj.latest_ui_discovery_run_id = record.id
                else:
                    record.status = UiDiscoveryRunStatus.error
                    record.error_message = result.get("error") or "Failed to parse inventory."
                    if result.get("raw_output"):
                        record.error_message = (
                            f"{record.error_message}\n\nRaw output snippet:\n{result['raw_output'][:2000]}"
                        )

                await db.commit()
        except Exception as exc:
            logger.exception("[UiDiscovery] run failed run_id=%s", run_id)
            try:
                async with async_session_maker() as db:
                    row = await db.execute(select(UiDiscoveryRun).where(UiDiscoveryRun.run_id == run_id))
                    record = row.scalar_one_or_none()
                    if record:
                        record.status = UiDiscoveryRunStatus.error
                        record.error_message = str(exc)
                        record.completed_at = datetime.utcnow()
                        await db.commit()
            except Exception:
                pass
        finally:
            clear_discovery_progress(run_id)

    async def get_status(self, run_id: str) -> UiDiscoveryStatusResponse:
        row = await self.db.execute(select(UiDiscoveryRun).where(UiDiscoveryRun.run_id == run_id))
        record = row.scalar_one_or_none()
        if not record:
            from fastapi import HTTPException, status as http_status

            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Discovery run not found")

        live = get_discovery_progress(run_id) or record.live_progress or {}
        inventory: Optional[UiInventory] = None
        if record.inventory_json:
            inventory = UiInventory.model_validate(record.inventory_json)

        pct = int(live.get("percentage") or (100 if record.status in ("completed", "error") else 0))
        pages = len(inventory.pages) if inventory else int(live.get("pages_discovered") or 0)

        return UiDiscoveryStatusResponse(
            run_id=run_id,
            status=record.status,
            percentage=pct,
            current_step=live.get("current_step"),
            platform=record.platform,
            actor_role=record.actor_role,
            app_url=record.app_url,
            inventory=inventory,
            partial_inventory=live.get("partial_inventory"),
            screenshots=list(live.get("screenshots") or record.screenshots or []),
            summary=record.summary,
            error_message=record.error_message,
            duration_ms=record.duration_ms,
            pages_discovered=pages,
            started_at=record.started_at,
            completed_at=record.completed_at,
        )

    async def get_latest(self, project_id: int) -> UiDiscoveryLatestResponse:
        proj = await self.db.get(Project, project_id)
        if not proj or not proj.latest_ui_discovery_run_id:
            return UiDiscoveryLatestResponse(found=False)

        record = await self.db.get(UiDiscoveryRun, proj.latest_ui_discovery_run_id)
        if not record or record.status != UiDiscoveryRunStatus.completed or not record.inventory_json:
            return UiDiscoveryLatestResponse(found=False)

        inventory = UiInventory.model_validate(record.inventory_json)
        discovered_at = inventory.discovered_at
        is_stale = False
        days_since: Optional[int] = None
        try:
            dt = datetime.fromisoformat(discovered_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - dt
            days_since = delta.days
            is_stale = days_since > STALE_DAYS
        except Exception:
            pass

        return UiDiscoveryLatestResponse(
            found=True,
            run_id=record.run_id,
            inventory=inventory,
            discovered_at=discovered_at,
            is_stale=is_stale,
            days_since_discovery=days_since,
        )

    async def get_history(self, project_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(UiDiscoveryRun)
            .where(UiDiscoveryRun.project_id == project_id)
            .order_by(UiDiscoveryRun.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        items = []
        for r in rows:
            pages = 0
            if r.inventory_json and isinstance(r.inventory_json, dict):
                pages = len(r.inventory_json.get("pages") or [])
            items.append(
                {
                    "id": r.id,
                    "run_id": r.run_id,
                    "status": r.status,
                    "platform": r.platform,
                    "actor_role": r.actor_role,
                    "app_url": r.app_url,
                    "pages_discovered": pages,
                    "duration_ms": r.duration_ms,
                    "created_at": r.created_at,
                    "completed_at": r.completed_at,
                }
            )
        return items
