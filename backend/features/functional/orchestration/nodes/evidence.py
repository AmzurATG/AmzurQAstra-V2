"""Evidence node: finalize per-case screenshot mapping."""
from __future__ import annotations

from typing import Any, Dict, List

from features.functional.orchestration.state import CaseResult, OrchestrationState


async def evidence_node(state: OrchestrationState) -> Dict[str, Any]:
    """Ensure each case result has a primary screenshot and live gallery paths."""
    results: List[CaseResult] = list(state.get("case_results") or [])
    retry_results: List[CaseResult] = list(state.get("retry_results") or [])
    by_case: Dict[int, CaseResult] = {}
    for r in results + retry_results:
        cid = int(r.get("test_case_id") or 0)
        if cid:
            # Retry wins over initial failure
            if r in retry_results or cid not in by_case:
                by_case[cid] = r

    live_shots: List[str] = []
    for r in by_case.values():
        path = r.get("screenshot_path")
        if path and path not in live_shots:
            live_shots.append(str(path))
        for log in r.get("agent_logs") or []:
            lp = log.get("screenshot_path")
            if lp and str(lp) not in live_shots:
                live_shots.append(str(lp))
    live_shots = live_shots[-24:]

    merged_results = list(by_case.values())
    already_retried = {int(r.get("test_case_id") or 0) for r in retry_results}

    def _is_suspicious_pass(r: CaseResult) -> bool:
        """A 'passed' case that produced no real evidence is not trustworthy."""
        if r.get("status") != "passed":
            return False
        steps = r.get("step_results") or []
        originals = r.get("original_steps") or []
        if originals and not steps:
            return True
        if int(r.get("duration_ms") or 0) <= 0:
            return True
        return False

    failed: List[int] = []
    for r in merged_results:
        cid = int(r["test_case_id"])
        status = r.get("status")
        if status not in ("passed", "cancelled", "skipped"):
            failed.append(cid)
        elif _is_suspicious_pass(r) and cid not in already_retried:
            # Re-verify suspiciously-empty passes with the stronger vision model.
            failed.append(cid)

    return {
        "case_results": merged_results,
        "failed_case_ids": failed,
        "status": "vision_retry" if failed else "reporting",
    }
