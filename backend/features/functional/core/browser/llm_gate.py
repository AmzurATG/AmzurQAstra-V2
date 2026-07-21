"""Shared LLM resilience gate for the orchestrated run-all pipeline.

A single process-wide gate sits in front of EVERY browser lane's LLM calls so
that N concurrent lanes behave like one well-mannered client against the shared
LiteLLM proxy. It provides four things the pipeline was missing:

1. Rate limiting   — a global concurrency semaphore + a requests/minute token
                     bucket, so 6 lanes can't saturate/rate-limit the proxy.
2. Circuit breaker — after repeated infra failures (429 / 5xx / timeout /
                     budget) the breaker trips OPEN and calls fail fast for a
                     cooldown instead of churning through hundreds of cases that
                     would all error identically (the run #14 failure mode).
3. Timeouts        — a hard per-call timeout so a hung request can't pin a lane.
4. Error taxonomy  — classify raw exceptions into budget / rate / timeout /
                     server / auth / other so the caller can retry the right
                     things and PAUSE (not fail) on unrecoverable infra errors.

The gate is intentionally a module-level singleton: it is shared across all
lanes/tasks in the same event loop and process.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Dict, Optional, TypeVar

from config import settings
from common.utils.logger import logger

T = TypeVar("T")


# ── Error taxonomy ───────────────────────────────────────────────────────────

class LLMErrorKind(str, Enum):
    BUDGET = "budget"      # proxy budget exhausted — will NOT self-heal
    RATE = "rate"          # 429 / rate limit — retryable with backoff
    TIMEOUT = "timeout"    # call exceeded timeout — retryable
    SERVER = "server"      # 5xx / overloaded / unavailable — retryable
    AUTH = "auth"          # 401 / 403 / bad key — not retryable, config problem
    OTHER = "other"        # anything else (often a real, non-infra error)


# Kinds that indicate an infrastructure problem (should influence the breaker).
_INFRA_KINDS = {
    LLMErrorKind.BUDGET,
    LLMErrorKind.RATE,
    LLMErrorKind.TIMEOUT,
    LLMErrorKind.SERVER,
}
# Kinds worth retrying at the case level.
_RETRYABLE_KINDS = {LLMErrorKind.RATE, LLMErrorKind.TIMEOUT, LLMErrorKind.SERVER}


class LLMGateError(Exception):
    """Base for gate-raised errors, carrying the classified kind."""

    def __init__(self, message: str, kind: LLMErrorKind) -> None:
        super().__init__(message)
        self.kind = kind


class LLMCircuitOpen(LLMGateError):
    """Raised immediately (no network call) while the breaker is OPEN."""

    def __init__(self, message: str, kind: LLMErrorKind = LLMErrorKind.SERVER) -> None:
        super().__init__(message, kind)


def classify_llm_error(exc: BaseException) -> LLMErrorKind:
    """Map a raw exception (proxy / SDK / asyncio) to an LLMErrorKind."""
    if isinstance(exc, LLMGateError):
        return exc.kind
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return LLMErrorKind.TIMEOUT

    msg = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    if "budget" in msg and ("exceed" in msg or "exceeded" in msg):
        return LLMErrorKind.BUDGET
    if status == 429 or "rate limit" in msg or "ratelimit" in msg or "too many requests" in msg:
        return LLMErrorKind.RATE
    if "timeout" in msg or "timed out" in msg:
        return LLMErrorKind.TIMEOUT
    if status in (500, 502, 503, 504) or any(
        s in msg for s in ("internal server error", "bad gateway", "service unavailable",
                            "overloaded", "gateway timeout", "502", "503", "504")
    ):
        return LLMErrorKind.SERVER
    if status in (401, 403) or any(
        s in msg for s in ("unauthorized", "unauthorised", "invalid api key",
                           "authentication", "forbidden", "401", "403")
    ):
        return LLMErrorKind.AUTH
    return LLMErrorKind.OTHER


def is_retryable_kind(kind: LLMErrorKind) -> bool:
    return kind in _RETRYABLE_KINDS


def is_infra_kind(kind: LLMErrorKind) -> bool:
    return kind in _INFRA_KINDS


# ── Token bucket (requests per minute) ───────────────────────────────────────

class _TokenBucket:
    """Simple async token bucket. rpm<=0 disables limiting."""

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
                # Wait for the next token to become available.
                deficit = 1.0 - self.tokens
                wait_s = deficit / self.refill_per_sec if self.refill_per_sec > 0 else 0.05
                await asyncio.sleep(min(max(wait_s, 0.01), 2.0))


# ── Circuit breaker ──────────────────────────────────────────────────────────

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _Breaker:
    failure_threshold: int
    cooldown_s: float
    budget_cooldown_s: float
    halfopen_probes: int
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at: float = 0.0
    open_until: float = 0.0
    halfopen_inflight: int = 0
    last_kind: Optional[LLMErrorKind] = None
    budget_exhausted: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def before_call(self) -> None:
        """Raise LLMCircuitOpen if the breaker is open; allow limited probes when half-open."""
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

    async def record_success(self) -> None:
        async with self._lock:
            if self.state != CircuitState.CLOSED:
                logger.info("[LLMGate] Circuit CLOSED — proxy healthy again")
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0
            self.halfopen_inflight = 0
            self.budget_exhausted = False
            self.last_kind = None

    async def record_failure(self, kind: LLMErrorKind) -> None:
        async with self._lock:
            self.last_kind = kind
            if kind == LLMErrorKind.BUDGET:
                # Budget won't recover on its own — open hard and mark exhausted.
                self.budget_exhausted = True
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                self.open_until = self.opened_at + self.budget_cooldown_s
                logger.error(
                    "[LLMGate] Circuit OPEN (budget exhausted) — pausing LLM calls for %.0fs",
                    self.budget_cooldown_s,
                )
                return
            # Half-open probe failed → reopen immediately.
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                self.open_until = self.opened_at + self.cooldown_s
                self.halfopen_inflight = 0
                logger.warning("[LLMGate] Circuit re-OPEN after failed probe (%s)", kind.value)
                return
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
                self.open_until = self.opened_at + self.cooldown_s
                logger.warning(
                    "[LLMGate] Circuit OPEN after %d consecutive %s failures — cooldown %.0fs",
                    self.consecutive_failures, kind.value, self.cooldown_s,
                )

    def snapshot(self) -> Dict[str, object]:
        now = time.monotonic()
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "budget_exhausted": self.budget_exhausted,
            "cooldown_remaining_s": max(0.0, self.open_until - now) if self.state == CircuitState.OPEN else 0.0,
            "last_kind": self.last_kind.value if self.last_kind else None,
        }


# ── Gate singleton ───────────────────────────────────────────────────────────

@dataclass
class _Metrics:
    calls: int = 0
    successes: int = 0
    failures: int = 0
    by_kind: Dict[str, int] = field(default_factory=dict)
    fast_failed_open: int = 0

    def record_kind(self, kind: LLMErrorKind) -> None:
        self.by_kind[kind.value] = self.by_kind.get(kind.value, 0) + 1


class LLMGate:
    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(max(1, int(getattr(settings, "LLM_MAX_INFLIGHT", 4) or 4)))
        self._bucket = _TokenBucket(int(getattr(settings, "LLM_RATE_LIMIT_RPM", 120) or 0))
        self._timeout = float(getattr(settings, "LLM_CALL_TIMEOUT_S", 90.0) or 90.0)
        self._breaker = _Breaker(
            failure_threshold=int(getattr(settings, "LLM_CB_FAILURE_THRESHOLD", 8) or 8),
            cooldown_s=float(getattr(settings, "LLM_CB_COOLDOWN_S", 30.0) or 30.0),
            budget_cooldown_s=float(getattr(settings, "LLM_CB_BUDGET_COOLDOWN_S", 900.0) or 900.0),
            halfopen_probes=int(getattr(settings, "LLM_CB_HALFOPEN_PROBES", 2) or 2),
        )
        self.metrics = _Metrics()

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Run an LLM coroutine factory through rate limit + breaker + timeout."""
        try:
            await self._breaker.before_call()
        except LLMCircuitOpen:
            self.metrics.fast_failed_open += 1
            raise

        await self._bucket.acquire()
        self.metrics.calls += 1
        async with self._sem:
            try:
                result = await asyncio.wait_for(fn(), timeout=self._timeout)
            except asyncio.TimeoutError:
                self.metrics.failures += 1
                self.metrics.record_kind(LLMErrorKind.TIMEOUT)
                await self._breaker.record_failure(LLMErrorKind.TIMEOUT)
                raise LLMGateError(
                    f"LLM call timed out after {self._timeout:.0f}s", LLMErrorKind.TIMEOUT
                )
            except Exception as exc:  # noqa: BLE001 — classify and re-raise
                kind = classify_llm_error(exc)
                self.metrics.failures += 1
                self.metrics.record_kind(kind)
                if is_infra_kind(kind):
                    await self._breaker.record_failure(kind)
                else:
                    # Non-infra (e.g. schema/validation) shouldn't trip the breaker.
                    await self._breaker.record_success()
                raise
            else:
                self.metrics.successes += 1
                await self._breaker.record_success()
                return result

    # Introspection used by the orchestrator to pause/resume cleanly.
    def should_pause(self) -> bool:
        snap = self._breaker.snapshot()
        return bool(snap["budget_exhausted"]) or snap["state"] == CircuitState.OPEN.value

    def is_budget_exhausted(self) -> bool:
        return self._breaker.budget_exhausted

    def snapshot(self) -> Dict[str, object]:
        return {
            "breaker": self._breaker.snapshot(),
            "metrics": {
                "calls": self.metrics.calls,
                "successes": self.metrics.successes,
                "failures": self.metrics.failures,
                "fast_failed_open": self.metrics.fast_failed_open,
                "by_kind": dict(self.metrics.by_kind),
            },
        }

    def reset(self) -> None:
        """Reset breaker + metrics at the start of a fresh run."""
        self._breaker.state = CircuitState.CLOSED
        self._breaker.consecutive_failures = 0
        self._breaker.budget_exhausted = False
        self._breaker.open_until = 0.0
        self._breaker.last_kind = None
        self.metrics = _Metrics()


_gate: Optional[LLMGate] = None


def get_gate() -> LLMGate:
    """Return the process-wide LLM gate singleton (lazy so config is loaded)."""
    global _gate
    if _gate is None:
        _gate = LLMGate()
    return _gate
