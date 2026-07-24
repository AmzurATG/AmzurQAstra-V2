"""Run Governor — pause / wait / resume / shed load based on LLM health."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from common.utils.logger import logger
from features.functional.core.browser.llm_gate import CircuitState, get_gate
from features.functional.core.status_narrator import live_status_banner

Action = Literal["continue", "wait", "pause", "shed"]


@dataclass
class GovernorDecision:
    action: Action
    wait_s: float = 0.0
    reason: str = ""
    banner: Optional[Dict[str, str]] = None
    shed_inflight: Optional[int] = None


class RunGovernor:
    """Decide whether to dispatch the next case or cool down."""

    def __init__(self) -> None:
        self._consecutive_waits = 0

    def evaluate(self) -> GovernorDecision:
        gate = get_gate()
        snap = gate.snapshot()
        br = snap.get("breaker") or {}
        state = str(br.get("state") or CircuitState.CLOSED.value)
        banner = live_status_banner(snap)
        cd = float(br.get("cooldown_remaining_s") or 0)
        kind = br.get("last_kind") or "infra"

        if state == CircuitState.OPEN.value or gate.is_budget_exhausted():
            wait = max(cd, 5.0)
            self._consecutive_waits += 1
            return GovernorDecision(
                action="wait" if self._consecutive_waits < 6 else "pause",
                wait_s=min(wait, 60.0),
                reason=f"circuit_{state}_{kind}",
                banner=banner,
            )

        if state == CircuitState.DEGRADED.value:
            self._consecutive_waits = 0
            return GovernorDecision(
                action="shed",
                reason="degraded_shed_load",
                banner=banner,
                shed_inflight=2,
            )

        if state == CircuitState.HALF_OPEN.value:
            self._consecutive_waits = 0
            return GovernorDecision(
                action="continue",
                reason="half_open_probe",
                banner=banner,
                shed_inflight=1,
            )

        self._consecutive_waits = 0
        return GovernorDecision(action="continue", reason="healthy")

    async def apply_before_case(
        self,
        *,
        run_id: int,
        progress_mgr: Any,
    ) -> GovernorDecision:
        decision = self.evaluate()
        if decision.banner:
            progress_mgr.update(
                run_id,
                {
                    "runtime_banner": decision.banner,
                    "llm_health": get_gate().snapshot(),
                    "current_test_case_title": decision.banner.get("message", "")[:120],
                },
            )
        elif decision.action == "continue":
            # Clear banner when healthy
            body = progress_mgr.get(run_id) or {}
            if body.get("runtime_banner"):
                progress_mgr.update(run_id, {"runtime_banner": None})

        if decision.action in ("wait", "pause"):
            logger.warning(
                "[RunGovernor] %s — %s (wait=%.0fs)",
                decision.action,
                decision.reason,
                decision.wait_s,
            )
            if decision.wait_s > 0:
                await asyncio.sleep(decision.wait_s)
            # Re-evaluate once after wait
            decision = self.evaluate()
            if decision.banner:
                progress_mgr.update(
                    run_id,
                    {
                        "runtime_banner": decision.banner,
                        "llm_health": get_gate().snapshot(),
                    },
                )
        return decision

    def health_prompt_hint(self) -> str:
        return get_gate().health_hint()
