"""Per-case time budgets — support short and long (5–15 min) cases."""
from __future__ import annotations

from typing import Any, Optional, Sequence

from config import settings


def format_duration_ms(ms: Optional[int | float]) -> str:
    """Human duration for UI / PDF: 850ms · 32s · 3m 12s · 1h 05m."""
    if ms is None:
        return "—"
    try:
        n = int(ms)
    except (TypeError, ValueError):
        return "—"
    if n < 0:
        n = 0
    if n < 1000:
        return f"{n}ms"
    secs = n / 1000.0
    if secs < 60:
        # Prefer whole seconds for live tables when nearly integer
        if abs(secs - round(secs)) < 0.05:
            return f"{int(round(secs))}s"
        return f"{secs:.1f}s"
    total_s = int(round(secs))
    hours, rem = divmod(total_s, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if seconds == 0:
        return f"{minutes}m"
    return f"{minutes}m {seconds:02d}s"


def wallclock_timeout_s(
    *,
    step_count: int = 0,
    reassign_count: int = 0,
    base_s: Optional[int] = None,
    long_s: Optional[int] = None,
    max_s: Optional[int] = None,
    long_step_threshold: Optional[int] = None,
) -> int:
    """
    Adaptive per-case wall-clock (seconds).

    - Typical cases: ~4 minutes (base)
    - Complex (many steps): ~10 minutes (long)
    - Reassigned / second chance: up to max (~15 minutes)
    """
    base = int(base_s if base_s is not None else getattr(settings, "TEST_CASE_WALLCLOCK_TIMEOUT_S", 240) or 240)
    long = int(long_s if long_s is not None else getattr(settings, "TEST_CASE_WALLCLOCK_LONG_S", 600) or 600)
    hard_max = int(max_s if max_s is not None else getattr(settings, "TEST_CASE_WALLCLOCK_MAX_S", 900) or 900)
    thresh = int(
        long_step_threshold
        if long_step_threshold is not None
        else getattr(settings, "TEST_CASE_LONG_STEP_THRESHOLD", 6)
        or 6
    )
    if base <= 0:
        return 0  # disabled

    long = max(long, base)
    hard_max = max(hard_max, long)

    if reassign_count >= 1:
        return hard_max

    n = max(0, int(step_count or 0))
    if n >= thresh:
        return long

    # Scale gently with step count (still capped at long)
    scaled = base + max(0, n - 3) * 30
    return min(max(base, scaled), long)


def budget_for_case(
    steps: Optional[Sequence[Any]] = None,
    *,
    reassign_count: int = 0,
) -> dict[str, Any]:
    n = len(list(steps or []))
    wc = wallclock_timeout_s(step_count=n, reassign_count=reassign_count)
    return {
        "step_count": n,
        "reassign_count": int(reassign_count or 0),
        "wallclock_timeout_s": wc,
        "wallclock_label": format_duration_ms(wc * 1000) if wc else "unlimited",
    }
