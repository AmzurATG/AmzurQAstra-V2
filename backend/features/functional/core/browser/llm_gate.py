"""Shared LLM resilience gate for the orchestrated run-all pipeline.

States:
  CLOSED   — healthy; prefer primary model
  DEGRADED — primary unhealthy; fallbacks allowed; soft shed load
  OPEN     — all models failing; fail-fast; Run Governor must pause
  HALF_OPEN — limited probes after cooldown

Also tracks per-model cooldowns so one bad Gemini deployment does not
block gpt-4o fallbacks.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from config import settings
from common.utils.logger import logger

T = TypeVar("T")


class LLMErrorKind(str, Enum):
    BUDGET = "budget"
    RATE = "rate"
    TIMEOUT = "timeout"
    SERVER = "server"
    AUTH = "auth"
    OTHER = "other"


_INFRA_KINDS = {
    LLMErrorKind.BUDGET,
    LLMErrorKind.RATE,
    LLMErrorKind.TIMEOUT,
    LLMErrorKind.SERVER,
}
_RETRYABLE_KINDS = {LLMErrorKind.RATE, LLMErrorKind.TIMEOUT, LLMErrorKind.SERVER}


class LLMGateError(Exception):
    def __init__(self, message: str, kind: LLMErrorKind) -> None:
        super().__init__(message)
        self.kind = kind


class LLMCircuitOpen(LLMGateError):
    def __init__(self, message: str, kind: LLMErrorKind = LLMErrorKind.SERVER) -> None:
        super().__init__(message, kind)


def classify_llm_error(exc: BaseException) -> LLMErrorKind:
    if isinstance(exc, LLMGateError):
        return exc.kind
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return LLMErrorKind.TIMEOUT

    msg = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    if "budget" in msg and ("exceed" in msg or "exceeded" in msg):
        return LLMErrorKind.BUDGET
    if (
        status == 429
        or "rate limit" in msg
        or "ratelimit" in msg
        or "too many requests" in msg
        or "no deployments available" in msg
        or "cooldown_list" in msg
    ):
        return LLMErrorKind.RATE
    if "timeout" in msg or "timed out" in msg:
        return LLMErrorKind.TIMEOUT
    if status in (500, 502, 503, 504) or any(
        s in msg
        for s in (
            "internal server error",
            "bad gateway",
            "service unavailable",
            "overloaded",
            "gateway timeout",
            "502",
            "503",
            "504",
        )
    ):
        return LLMErrorKind.SERVER
    if status in (401, 403) or any(
        s in msg
        for s in (
            "unauthorized",
            "unauthorised",
            "invalid api key",
            "authentication",
            "forbidden",
            "401",
            "403",
        )
    ):
        return LLMErrorKind.AUTH
    return LLMErrorKind.OTHER


def is_retryable_kind(kind: LLMErrorKind) -> bool:
    return kind in _RETRYABLE_KINDS


def is_infra_kind(kind: LLMErrorKind) -> bool:
    return kind in _INFRA_KINDS


class _TokenBucket:
    def __init__(self, rpm: int) -> None:
        self.rpm = max(0, int(rpm))
        self.capacity = float(max(1, self.rpm))
        self.tokens = self.capacity
        self.refill_per_sec = self.rpm / 60.0 if self.rpm > 0 else 0.0
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self.rpm <= 0:
            return
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.updated
                self.updated = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                deficit = 1.0 - self.tokens
                wait_s = deficit / self.refill_per_sec if self.refill_per_sec > 0 else 0.05
                await asyncio.sleep(min(max(wait_s, 0.01), 2.0))


class CircuitState(str, Enum):
    CLOSED = "closed"
    DEGRADED = "degraded"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _Breaker:
    failure_threshold: int
    degrade_threshold: int
    cooldown_s: float
    budget_cooldown_s: float
    halfopen_probes: int
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_all_model_failures: int = 0
    opened_at: float = 0.0
    open_until: float = 0.0
    halfopen_inflight: int = 0
    last_kind: Optional[LLMErrorKind] = None
    budget_exhausted: bool = False
    active_model: Optional[str] = None
    preferred_model: Optional[str] = None
    # model_id -> cooldown_until monotonic
    model_cooldown_until: Dict[str, float] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def model_available(self, model: str, *, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.monotonic()
        until = self.model_cooldown_until.get(model)
        if until is None:
            return True
        return t >= until

    async def mark_model_cooldown(self, model: str, kind: LLMErrorKind) -> None:
        async with self._lock:
            now = time.monotonic()
            # Rate limits often ask ~30s; budget gets long cooldown.
            cd = self.budget_cooldown_s if kind == LLMErrorKind.BUDGET else self.cooldown_s
            self.model_cooldown_until[model] = now + cd
            self.last_kind = kind
            self.consecutive_failures += 1
            if self.state == CircuitState.CLOSED and self.consecutive_failures >= self.degrade_threshold:
                self.state = CircuitState.DEGRADED
                logger.warning(
                    "[LLMGate] Circuit DEGRADED after %d infra failures — prefer fallbacks",
                    self.consecutive_failures,
                )
            if kind == LLMErrorKind.BUDGET:
                self.budget_exhausted = True

    async def before_call(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.OPEN:
                if now >= self.open_until:
                    self.state = CircuitState.HALF_OPEN
                    self.halfopen_inflight = 0
                    logger.warning("[LLMGate] Circuit HALF_OPEN — probing proxy recovery")
                else:
                    raise LLMCircuitOpen(
                        f"LLM circuit open ({self.last_kind or 'infra'}); "
                        f"cooling down {self.open_until - now:.0f}s",
                        kind=self.last_kind or LLMErrorKind.SERVER,
                    )
            if self.state == CircuitState.HALF_OPEN:
                if self.halfopen_inflight >= self.halfopen_probes:
                    raise LLMCircuitOpen(
                        "LLM circuit half-open; probe limit reached",
                        kind=self.last_kind or LLMErrorKind.SERVER,
                    )
                self.halfopen_inflight += 1

    async def record_success(self, *, model: Optional[str] = None) -> None:
        async with self._lock:
            prev = self.state
            if model:
                self.active_model = model
                self.model_cooldown_until.pop(model, None)
            self.consecutive_failures = 0
            self.consecutive_all_model_failures = 0
            self.halfopen_inflight = 0
            self.budget_exhausted = False
            self.last_kind = None
            # Half-open or degraded success on any model → closed if preferred recovered,
            # else stay degraded until preferred succeeds.
            if prev == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("[LLMGate] Circuit CLOSED — proxy healthy again")
            elif prev == CircuitState.DEGRADED:
                preferred = self.preferred_model
                if not preferred or (model and model == preferred):
                    self.state = CircuitState.CLOSED
                    logger.info("[LLMGate] Circuit CLOSED — primary recovered")
                else:
                    self.state = CircuitState.DEGRADED
            else:
                self.state = CircuitState.CLOSED

    async def record_failure(self, kind: LLMErrorKind, *, model: Optional[str] = None) -> None:
        async with self._lock:
            self.last_kind = kind
            if model:
                now = time.monotonic()
                cd = self.budget_cooldown_s if kind == LLMErrorKind.BUDGET else self.cooldown_s
                self.model_cooldown_until[model] = now + cd

            if kind == LLMErrorKind.BUDGET:
                self.budget_exhausted = True
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                self.open_until = self.opened_at + self.budget_cooldown_s
                logger.error(
                    "[LLMGate] Circuit OPEN (budget exhausted) — pausing LLM for %.0fs",
                    self.budget_cooldown_s,
                )
                return

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                self.open_until = self.opened_at + self.cooldown_s
                self.halfopen_inflight = 0
                logger.warning("[LLMGate] Circuit re-OPEN after failed probe (%s)", kind.value)
                return

            self.consecutive_failures += 1
            if self.state == CircuitState.CLOSED and self.consecutive_failures >= self.degrade_threshold:
                self.state = CircuitState.DEGRADED
                logger.warning(
                    "[LLMGate] Circuit DEGRADED after %d consecutive %s failures",
                    self.consecutive_failures,
                    kind.value,
                )

            # OPEN only after sustained all-model / hard failures
            if self.consecutive_all_model_failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                self.open_until = self.opened_at + self.cooldown_s
                logger.warning(
                    "[LLMGate] Circuit OPEN after %d all-model failures — cooldown %.0fs",
                    self.consecutive_all_model_failures,
                    self.cooldown_s,
                )

    async def record_all_models_failed(self, kind: LLMErrorKind) -> None:
        async with self._lock:
            self.last_kind = kind
            self.consecutive_all_model_failures += 1
            self.consecutive_failures += 1
            if self.state != CircuitState.OPEN:
                if self.consecutive_all_model_failures >= max(2, self.failure_threshold // 2):
                    self.state = CircuitState.OPEN
                    self.opened_at = time.monotonic()
                    self.open_until = self.opened_at + self.cooldown_s
                    logger.warning(
                        "[LLMGate] Circuit OPEN — all models failed (%s); cooldown %.0fs",
                        kind.value,
                        self.cooldown_s,
                    )
                elif self.state == CircuitState.CLOSED:
                    self.state = CircuitState.DEGRADED

    def snapshot(self) -> Dict[str, object]:
        now = time.monotonic()
        model_cds = {
            m: max(0.0, until - now)
            for m, until in self.model_cooldown_until.items()
            if until > now
        }
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_all_model_failures": self.consecutive_all_model_failures,
            "budget_exhausted": self.budget_exhausted,
            "cooldown_remaining_s": (
                max(0.0, self.open_until - now) if self.state == CircuitState.OPEN else 0.0
            ),
            "last_kind": self.last_kind.value if self.last_kind else None,
            "active_model": self.active_model,
            "preferred_model": self.preferred_model,
            "model_cooldowns": model_cds,
            "degraded": self.state in (CircuitState.DEGRADED, CircuitState.OPEN),
        }


@dataclass
class _Metrics:
    calls: int = 0
    successes: int = 0
    failures: int = 0
    by_kind: Dict[str, int] = field(default_factory=dict)
    fast_failed_open: int = 0
    fallback_successes: int = 0

    def record_kind(self, kind: LLMErrorKind) -> None:
        self.by_kind[kind.value] = self.by_kind.get(kind.value, 0) + 1


class LLMGate:
    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(max(1, int(getattr(settings, "LLM_MAX_INFLIGHT", 4) or 4)))
        self._bucket = _TokenBucket(int(getattr(settings, "LLM_RATE_LIMIT_RPM", 120) or 0))
        self._timeout = float(getattr(settings, "LLM_CALL_TIMEOUT_S", 90.0) or 90.0)
        self._breaker = _Breaker(
            failure_threshold=int(getattr(settings, "LLM_CB_FAILURE_THRESHOLD", 8) or 8),
            degrade_threshold=int(getattr(settings, "LLM_CB_DEGRADE_THRESHOLD", 3) or 3),
            cooldown_s=float(getattr(settings, "LLM_CB_COOLDOWN_S", 30.0) or 30.0),
            budget_cooldown_s=float(getattr(settings, "LLM_CB_BUDGET_COOLDOWN_S", 900.0) or 900.0),
            halfopen_probes=int(getattr(settings, "LLM_CB_HALFOPEN_PROBES", 2) or 2),
        )
        self.metrics = _Metrics()

    def set_preferred_model(self, model: str) -> None:
        self._breaker.preferred_model = model

    def model_available(self, model: str) -> bool:
        return self._breaker.model_available(model)

    async def call(
        self,
        fn: Callable[[], Awaitable[T]],
        *,
        model: Optional[str] = None,
        is_fallback: bool = False,
    ) -> T:
        try:
            await self._breaker.before_call()
        except LLMCircuitOpen:
            self.metrics.fast_failed_open += 1
            raise

        if model and not self._breaker.model_available(model):
            # Soft skip — caller should try next model; raise RATE so chain continues.
            raise LLMGateError(
                f"Model {model} in cooldown",
                LLMErrorKind.RATE,
            )

        await self._bucket.acquire()
        self.metrics.calls += 1
        async with self._sem:
            try:
                result = await asyncio.wait_for(fn(), timeout=self._timeout)
            except asyncio.TimeoutError:
                self.metrics.failures += 1
                self.metrics.record_kind(LLMErrorKind.TIMEOUT)
                await self._breaker.record_failure(LLMErrorKind.TIMEOUT, model=model)
                raise LLMGateError(
                    f"LLM call timed out after {self._timeout:.0f}s", LLMErrorKind.TIMEOUT
                )
            except Exception as exc:  # noqa: BLE001
                kind = classify_llm_error(exc)
                self.metrics.failures += 1
                self.metrics.record_kind(kind)
                if is_infra_kind(kind):
                    await self._breaker.record_failure(kind, model=model)
                else:
                    await self._breaker.record_success(model=model)
                raise
            else:
                self.metrics.successes += 1
                if is_fallback:
                    self.metrics.fallback_successes += 1
                await self._breaker.record_success(model=model)
                return result

    async def record_chain_exhausted(self, kind: LLMErrorKind) -> None:
        await self._breaker.record_all_models_failed(kind)

    def should_pause(self) -> bool:
        snap = self._breaker.snapshot()
        return bool(snap["budget_exhausted"]) or snap["state"] == CircuitState.OPEN.value

    def is_degraded(self) -> bool:
        return self._breaker.state in (CircuitState.DEGRADED, CircuitState.OPEN)

    def is_budget_exhausted(self) -> bool:
        return self._breaker.budget_exhausted

    def health_hint(self) -> str:
        snap = self._breaker.snapshot()
        state = snap["state"]
        kind = snap.get("last_kind") or "unknown"
        cd = float(snap.get("cooldown_remaining_s") or 0)
        active = snap.get("active_model") or "unknown"
        if state == CircuitState.OPEN.value:
            return (
                f"RUNTIME HEALTH: LLM circuit OPEN ({kind}). "
                f"Cooling down ~{cd:.0f}s. Do not invent UI success; "
                "finish safely and emit VERDICT_JSON reflecting blocked execution if needed."
            )
        if state == CircuitState.DEGRADED.value:
            return (
                f"RUNTIME HEALTH: LLM DEGRADED ({kind}). "
                f"Prefer stable fallback models; active≈{active}. "
                "Keep steps short; still capture evidence screenshots."
            )
        if state == CircuitState.HALF_OPEN.value:
            return "RUNTIME HEALTH: LLM recovering (half-open). Prefer concise actions."
        return ""

    def snapshot(self) -> Dict[str, Any]:
        return {
            "breaker": self._breaker.snapshot(),
            "metrics": {
                "calls": self.metrics.calls,
                "successes": self.metrics.successes,
                "failures": self.metrics.failures,
                "fast_failed_open": self.metrics.fast_failed_open,
                "fallback_successes": self.metrics.fallback_successes,
                "by_kind": dict(self.metrics.by_kind),
            },
            "health_hint": self.health_hint(),
        }

    def reset(self) -> None:
        self._breaker.state = CircuitState.CLOSED
        self._breaker.consecutive_failures = 0
        self._breaker.consecutive_all_model_failures = 0
        self._breaker.budget_exhausted = False
        self._breaker.open_until = 0.0
        self._breaker.last_kind = None
        self._breaker.model_cooldown_until.clear()
        self._breaker.active_model = None
        self.metrics = _Metrics()


_gate: Optional[LLMGate] = None


def get_gate() -> LLMGate:
    global _gate
    if _gate is None:
        _gate = LLMGate()
    return _gate
