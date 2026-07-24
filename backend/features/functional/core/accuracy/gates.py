"""Screenshot + verdict accuracy gates."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from config import settings
from features.functional.core.accuracy.types import EvidenceQuality, VerdictSource


def count_screenshots(
    screenshots: Optional[Sequence[str]] = None,
    agent_logs: Optional[Sequence[Dict[str, Any]]] = None,
) -> int:
    paths: set[str] = set()
    for p in screenshots or []:
        if p:
            paths.add(str(p))
    for entry in agent_logs or []:
        if isinstance(entry, dict) and entry.get("screenshot_path"):
            paths.add(str(entry["screenshot_path"]))
    return len(paths)


class ScreenshotGate:
    @staticmethod
    def evaluate(
        *,
        capture_screenshots: bool,
        screenshots: Optional[Sequence[str]] = None,
        agent_logs: Optional[Sequence[Dict[str, Any]]] = None,
        overall: Optional[str] = None,
        infra_error: bool = False,
    ) -> Optional[Dict[str, Any]]:
        if not capture_screenshots or not getattr(settings, "ACCURACY_REQUIRE_SCREENSHOTS", True):
            return None
        if infra_error or overall in ("cancelled", "skipped"):
            return None
        if count_screenshots(screenshots, agent_logs) > 0:
            return None
        return {
            "status": "error",
            "overall": "error",
            "infra_error": True,
            "error_kind": EvidenceQuality.MISSING_SCREENSHOTS.value,
            "error": EvidenceQuality.MISSING_SCREENSHOTS.value,
            "summary": "Accuracy gate: no screenshots captured. Re-run required.",
        }


class VerdictGate:
    @staticmethod
    def tag_verdict(verdict: Dict[str, Any], source: VerdictSource) -> Dict[str, Any]:
        out = dict(verdict)
        out["verdict_source"] = source.value
        if source in (VerdictSource.FALLBACK, VerdictSource.INCONCLUSIVE):
            if getattr(settings, "ACCURACY_REQUIRE_PARSED_VERDICT", True):
                out["inconclusive"] = True
        return out

    @staticmethod
    def exhausted_payload(
        *,
        screenshots: List[str],
        agent_logs: List[Dict[str, Any]],
        steps_total: int,
        duration_ms: int,
        source: str = VerdictSource.FALLBACK.value,
        original_steps: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        from features.functional.core.status_narrator import infra_step_stubs, user_message_for

        stubs = infra_step_stubs(
            list(original_steps or []),
            error_kind=EvidenceQuality.MISSING_VERDICT_JSON.value,
            summary=user_message_for(EvidenceQuality.MISSING_VERDICT_JSON.value),
        )
        if not stubs and steps_total > 0:
            stubs = infra_step_stubs(
                [{"step_number": i + 1} for i in range(steps_total)],
                error_kind=EvidenceQuality.MISSING_VERDICT_JSON.value,
            )
        msg = user_message_for(EvidenceQuality.MISSING_VERDICT_JSON.value)
        return {
            "status": "error",
            "overall": "error",
            "screenshots": list(screenshots),
            "logs": agent_logs,
            "step_results": stubs,
            "steps_total": len(stubs) or steps_total,
            "steps_passed": 0,
            "steps_failed": 0,
            "summary": msg,
            "duration_ms": duration_ms,
            "error": EvidenceQuality.MISSING_VERDICT_JSON.value,
            "user_message": msg,
            "infra_error": True,
            "error_kind": EvidenceQuality.MISSING_VERDICT_JSON.value,
            "verdict_source": source,
        }
