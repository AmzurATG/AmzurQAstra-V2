"""UI re-check agent — vision LLM judges screenshots vs expected steps."""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from common.llm.base import Message
from common.llm.factory import get_llm_client
from common.utils.logger import logger
from config import settings
from features.functional.core.llm_prompts.registry import get_prompt
from features.functional.core.llm_prompts.ui_validation import build_ui_validation_user_prompt
from features.functional.core.ui_validation.schemas import UiValidationResult


def _resolve_screenshot_path(path: str) -> Optional[Path]:
    if not path:
        return None
    p = Path(path)
    if p.is_file():
        return p
    # Paths are often stored as /screenshots/<file> relative to SCREENSHOTS_DIR parent
    root = Path(settings.SCREENSHOTS_DIR)
    name = p.name
    candidate = root / name
    if candidate.is_file():
        return candidate
    # Strip leading /screenshots/
    parts = p.parts
    if "screenshots" in parts:
        idx = parts.index("screenshots")
        candidate = root.joinpath(*parts[idx + 1 :])
        if candidate.is_file():
            return candidate
    return None


def _image_parts(paths: Sequence[str], *, max_images: int = 8) -> List[Dict[str, Any]]:
    parts: List[Dict[str, Any]] = []
    for raw in list(paths)[-max_images:]:
        fp = _resolve_screenshot_path(str(raw))
        if not fp:
            continue
        try:
            data = fp.read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            mime = "image/png" if fp.suffix.lower() == ".png" else "image/jpeg"
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )
        except Exception as exc:
            logger.warning("[UiValidation] failed to load screenshot %s: %s", fp, exc)
    return parts


def _parse_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Common LLM glitch: trailing commas before } or ]
        fixed = re.sub(r",\s*([}\]])", r"\1", raw)
        return json.loads(fixed)


class UiValidationAgent:
    """Vision-based second opinion for case outcomes."""

    async def validate(
        self,
        *,
        title: str,
        description: str,
        expected_steps: List[Dict[str, Any]],
        screenshot_paths: Sequence[str],
        executor_status: str,
        executor_summary: str = "",
    ) -> UiValidationResult:
        if not screenshot_paths:
            return UiValidationResult(
                ui_verdict="inconclusive",
                confidence=0.0,
                ui_observations=["No screenshots available for UI validation."],
            )

        model = (
            (getattr(settings, "UI_VALIDATION_MODEL", "") or "").strip()
            or getattr(settings, "BROWSER_USE_LLM_MODEL", None)
            or settings.LITELLM_MODEL
        )
        version, system = get_prompt("ui_validation")
        user_text = build_ui_validation_user_prompt(
            title=title,
            description=description,
            expected_steps=expected_steps,
            executor_status=executor_status,
            executor_summary=executor_summary,
        )
        content: List[Dict[str, Any]] = [{"type": "text", "text": user_text}]
        content.extend(_image_parts(screenshot_paths))

        client = get_llm_client(provider="litellm", model=model)
        try:
            resp = await client.chat(
                messages=[
                    Message(role="system", content=system),
                    Message(role="user", content=content),
                ],
                model=model,
                temperature=0.1,
                max_tokens=1200,
            )
            data = _parse_json(resp.content or "")
        except Exception as exc:
            logger.warning("[UiValidation] agent failed: %s", exc)
            return UiValidationResult(
                ui_verdict="inconclusive",
                confidence=0.0,
                ui_observations=[f"UI validation error: {str(exc)[:200]}"],
                raw_summary=str(exc)[:300],
            )

        verdict = str(data.get("ui_verdict") or "inconclusive").lower()
        if verdict not in ("passed", "failed", "inconclusive"):
            verdict = "inconclusive"
        try:
            confidence = float(data.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        step_checks = []
        for sc in data.get("step_checks") or []:
            if not isinstance(sc, dict):
                continue
            step_checks.append(
                {
                    "step": int(sc.get("step") or 0),
                    "status": str(sc.get("status") or "inconclusive"),
                    "evidence": sc.get("evidence"),
                    "why": sc.get("why"),
                }
            )

        result = UiValidationResult(
            ui_verdict=verdict,
            confidence=confidence,
            step_checks=step_checks,  # type: ignore[arg-type]
            ui_observations=[str(x) for x in (data.get("ui_observations") or [])][:12],
            disagrees_with_executor=(
                verdict in ("passed", "failed") and verdict != str(executor_status).lower()
            ),
            raw_summary=str(data.get("summary") or "")[:500],
        )
        logger.info(
            "[UiValidation] prompt=ui_validation@%s verdict=%s conf=%.2f model=%s",
            version, result.ui_verdict, result.confidence, model,
        )
        return result
