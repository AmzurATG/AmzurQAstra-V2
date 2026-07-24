"""Thin Observe → Think → Act → Check helper for rule-based agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional


ObserveFn = Callable[[], Awaitable[Any] | Any]
ThinkFn = Callable[[Any], Awaitable[Any] | Any]
ActFn = Callable[[Any], Awaitable[Any] | Any]
CheckFn = Callable[[Any, Any], Awaitable[bool] | bool]


@dataclass
class ReactResult:
    ok: bool
    observation: Any = None
    thought: Any = None
    action: Any = None
    attempts: int = 0


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value  # type: ignore[misc]
    return value


async def react_once(
    *,
    observe: ObserveFn,
    think: ThinkFn,
    act: ActFn,
    check: CheckFn,
    retries: int = 1,
) -> ReactResult:
    """Run one ReAct cycle; optionally retry once if check fails."""
    last: ReactResult = ReactResult(ok=False)
    for attempt in range(1, max(1, retries) + 2):
        obs = await _maybe_await(observe())
        thought = await _maybe_await(think(obs))
        if thought is None:
            return ReactResult(ok=True, observation=obs, thought=None, action=None, attempts=attempt)
        action = await _maybe_await(act(thought))
        ok = bool(await _maybe_await(check(obs, action)))
        last = ReactResult(ok=ok, observation=obs, thought=thought, action=action, attempts=attempt)
        if ok:
            return last
        if attempt > retries:
            break
    return last
