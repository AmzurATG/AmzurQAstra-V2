"""UI validate node: vision re-check after execute / vision_retry."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Set

from common.utils.logger import logger
from config import settings
from features.functional.core.accuracy.final_status import resolve_final_status
from features.functional.core.accuracy.gates import count_screenshots
from features.functional.core.accuracy.types import VerdictSource
from features.functional.core.ui_validation.agent import UiValidationAgent
from features.functional.orchestration.result_persistence import persist_single_result
from features.functional.orchestration.state import CaseResult, OrchestrationState
from features.functional.services.run_progress_manager import RunProgressManager


def _shot_paths(r: CaseResult) -> List[str]:
    paths: List[str] = []
    if r.get("screenshot_path"):
        paths.append(str(r["screenshot_path"]))
    for log in r.get("agent_logs") or []:
        if isinstance(log, dict) and log.get("screenshot_path"):
            paths.append(str(log["screenshot_path"]))
    # de-dupe preserve order
    seen: Set[str] = set()
    out: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _should_validate(r: CaseResult, *, sample_rate: float, rng: random.Random) -> bool:
    status = str(r.get("status") or "")
    if r.get("infra_error"):
        return False
    if status in ("cancelled", "skipped"):
        return False
    vs = str(
        r.get("verdict_source")
        or (r.get("ai_modified") or {}).get("verdict_source")
        or ""
    )
    if status in ("failed", "error"):
        return True
    if vs in (VerdictSource.FALLBACK.value, VerdictSource.INCONCLUSIVE.value):
        return True
    if status == "passed":
        return rng.random() < max(0.0, min(1.0, sample_rate))
    return False


async def ui_validate_node(state: OrchestrationState) -> Dict[str, Any]:
    if not bool(getattr(settings, "UI_VALIDATION_ENABLED", True)):
        return {"status": "reporting"}

    # Shed UiValidation load when the LLM circuit is OPEN / heavily degraded.
    try:
        from features.functional.core.browser.llm_gate import CircuitState, get_gate

        snap = get_gate().snapshot()
        br = snap.get("breaker") or {}
        if br.get("state") == CircuitState.OPEN.value or br.get("budget_exhausted"):
            logger.warning("[UiValidate] Skipping — LLM circuit open / budget exhausted")
            return {"status": "reporting", "ui_validation_skipped": True}
        if br.get("state") == CircuitState.DEGRADED.value:
            # Only validate failures while degraded (cut sample to ~0 for passes).
            sample_rate_override = 0.0
        else:
            sample_rate_override = None
    except Exception:
        sample_rate_override = None

    run_id = int(state["run_id"])
    progress_mgr = RunProgressManager()
    if progress_mgr.is_cancel_requested(run_id):
        return {"status": "cancelled", "cancel_requested": True}

    results: List[CaseResult] = list(state.get("case_results") or [])
    if not results:
        return {"status": "reporting"}

    case_map = {int(c["test_case_id"]): c for c in (state.get("cases") or [])}
    sample_rate = (
        sample_rate_override
        if sample_rate_override is not None
        else float(getattr(settings, "UI_VALIDATION_PASS_SAMPLE_RATE", 0.15) or 0.15)
    )
    rng = random.Random(run_id)  # deterministic per run
    agent = UiValidationAgent()
    updated: List[CaseResult] = []

    progress_mgr.update(
        run_id,
        {
            "current_test_case_title": "UI validation (re-checking screenshots)…",
            "status": "ui_validating",
        },
    )

    for r in results:
        cr = dict(r)
        if not _should_validate(cr, sample_rate=sample_rate, rng=rng):
            updated.append(CaseResult(**cr))  # type: ignore[misc]
            continue

        shots = _shot_paths(cr)
        if count_screenshots(shots, None) <= 0:
            updated.append(CaseResult(**cr))  # type: ignore[misc]
            continue

        cid = int(cr.get("test_case_id") or 0)
        case = case_map.get(cid) or {}
        title = str(cr.get("title") or case.get("title") or f"Case {cid}")
        executor_status = str(cr.get("status") or "error")

        try:
            ui = await agent.validate(
                title=title,
                description=str(case.get("description") or ""),
                expected_steps=list(case.get("steps") or cr.get("original_steps") or []),
                screenshot_paths=shots,
                executor_status=executor_status,
                executor_summary=str(cr.get("error") or ""),
            )
        except Exception as exc:
            logger.warning("[UiValidate] case %s failed: %s", cid, exc)
            updated.append(CaseResult(**cr))  # type: ignore[misc]
            continue

        decision = resolve_final_status(
            executor_status=executor_status,
            ui_verdict=ui.ui_verdict,
            ui_confidence=ui.confidence,
            ui_payload=ui.as_dict(),
            has_screenshots=True,
        )
        cr["executor_status"] = decision.get("executor_status") or executor_status
        cr["ui_override"] = bool(decision.get("ui_override"))
        cr["ui_validation"] = decision.get("ui_validation") or ui.as_dict()
        cr["status"] = str(decision.get("status") or executor_status)
        if decision.get("error_kind"):
            cr["error_kind"] = decision["error_kind"]
            cr["error"] = decision.get("error") or cr.get("error")
        ai = dict(cr.get("ai_modified") or {})
        ai["ui_override"] = cr["ui_override"]
        ai["ui_validation"] = cr["ui_validation"]
        ai["executor_status"] = cr["executor_status"]
        cr["ai_modified"] = ai

        await persist_single_result(CaseResult(**cr))  # type: ignore[misc]
        updated.append(CaseResult(**cr))  # type: ignore[misc]

    return {
        "case_results": updated,
        "status": "reporting",
    }
