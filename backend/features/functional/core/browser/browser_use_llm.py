"""
LLM factory for browser-use: LiteLLM proxy (default) or direct Google Gemini.

Returns (primary, fallback_llm) for Agent(llm=..., fallback_llm=...).
Every ainvoke goes through the shared LLM gate with per-model cooldowns.
"""
from __future__ import annotations

from typing import Any, List, Optional

from config import settings
from common.utils.logger import logger


def _fallback_model_ids(primary: str) -> List[str]:
    """Primary first, then BROWSER_USE / LITELLM fallbacks (deduped)."""
    raw = (
        getattr(settings, "BROWSER_USE_FALLBACK_MODELS", None)
        or getattr(settings, "LITELLM_FALLBACK_MODELS", None)
        or "gpt-4o"
    )
    seen: set[str] = set()
    out: List[str] = []
    for m in [primary] + [x.strip() for x in str(raw).split(",")]:
        if not m or m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out


def _build_gated_openai_class():
    from browser_use import ChatOpenAI
    from features.functional.core.browser.llm_gate import (
        LLMErrorKind,
        classify_llm_error,
        get_gate,
        is_retryable_kind,
    )

    class GatedChatOpenAI(ChatOpenAI):  # type: ignore[misc]
        # Optional sibling models for same-call failover (set by factory).
        _sibling_models: List[Any] = []
        _sibling_ids: List[str] = []

        async def ainvoke(self, messages: Any, output_format: Any = None, **kwargs: Any):  # type: ignore[override]
            gate = get_gate()
            model_id = str(getattr(self, "model", None) or getattr(self, "model_name", None) or "")
            chain = [(self, model_id)]
            for sib, sid in zip(getattr(self, "_sibling_models", []) or [], getattr(self, "_sibling_ids", []) or []):
                if sib is not self and sid != model_id:
                    chain.append((sib, sid))

            last_exc: Optional[BaseException] = None
            for i, (llm, mid) in enumerate(chain):
                if mid and not gate.model_available(mid) and i < len(chain) - 1:
                    logger.info("[BrowserLLM] skip %s (cooldown)", mid)
                    continue
                try:
                    is_fb = i > 0
                    # Sibling models are also GatedChatOpenAI — call underlying without
                    # re-entering sibling chain (use ChatOpenAI.ainvoke via gate only).
                    async def _call(_llm=llm):
                        return await super(GatedChatOpenAI, _llm).ainvoke(
                            messages, output_format, **kwargs
                        )

                    result = await gate.call(
                        _call,
                        model=mid or None,
                        is_fallback=is_fb,
                    )
                    if is_fb:
                        logger.info("[BrowserLLM] fallback succeeded model=%s", mid)
                    return result
                except BaseException as exc:  # noqa: BLE001
                    last_exc = exc
                    kind = classify_llm_error(exc)
                    logger.warning(
                        "[BrowserLLM] model=%s failed (%s): %s",
                        mid,
                        kind.value,
                        str(exc)[:160],
                    )
                    if not is_retryable_kind(kind) and kind not in (
                        LLMErrorKind.RATE,
                        LLMErrorKind.SERVER,
                        LLMErrorKind.TIMEOUT,
                    ):
                        if i == len(chain) - 1:
                            break
                        continue
                    continue
            if last_exc is not None:
                await gate.record_chain_exhausted(classify_llm_error(last_exc))
                raise last_exc
            raise RuntimeError("Browser LLM model chain exhausted")

    return GatedChatOpenAI


def _make_openai_llm(model: str, gated_cls: type):
    if not settings.LITELLM_API_KEY or not settings.LITELLM_API_BASE:
        raise ValueError(
            "Browser agent uses LiteLLM proxy by default. Set LITELLM_API_KEY and LITELLM_API_BASE."
        )
    base = settings.LITELLM_API_BASE.strip().rstrip("/")
    return gated_cls(
        model=model,
        api_key=settings.LITELLM_API_KEY.strip(),
        base_url=base,
        temperature=settings.BROWSER_USE_LLM_TEMPERATURE,
        frequency_penalty=None,
        max_retries=1,
    )


def get_browser_use_llm(model_override: str | None = None):
    primary, _ = get_browser_use_llms(model_override=model_override)
    return primary


def get_browser_use_llms(model_override: str | None = None) -> tuple[Any, Optional[Any]]:
    """
    Return (primary_llm, fallback_llm) for browser-use Agent.

    Primary ainvoke tries sibling fallbacks on RATE/SERVER before failing.
    fallback_llm is also passed to Agent for browser-use's own failover path.
    """
    backend = (settings.BROWSER_USE_LLM_BACKEND or "litellm").strip().lower()
    override = (model_override or "").strip() or None

    if backend == "google":
        from browser_use import ChatGoogle

        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "BROWSER_USE_LLM_BACKEND=google requires GEMINI_API_KEY in .env"
            )
        model = override or (settings.BROWSER_USE_LLM_MODEL or "gemini-2.0-flash").strip()
        llm = ChatGoogle(
            model=model,
            api_key=settings.GEMINI_API_KEY.strip(),
            temperature=settings.BROWSER_USE_LLM_TEMPERATURE,
        )
        return llm, None

    gated_cls = _build_gated_openai_class()
    primary_id = override or (settings.BROWSER_USE_LLM_MODEL or settings.LITELLM_MODEL).strip()
    ids = _fallback_model_ids(primary_id)

    from features.functional.core.browser.llm_gate import get_gate

    gate = get_gate()
    gate.set_preferred_model(ids[0])

    models = [_make_openai_llm(mid, gated_cls) for mid in ids]
    # Wire siblings onto each instance for same-call failover (primary owns the chain).
    primary = models[0]
    primary._sibling_models = models[1:]  # type: ignore[attr-defined]
    primary._sibling_ids = ids[1:]  # type: ignore[attr-defined]

    fallback = models[1] if len(models) > 1 else None
    if fallback is not None:
        # Fallback instance should not recurse into full chain again.
        fallback._sibling_models = models[2:]  # type: ignore[attr-defined]
        fallback._sibling_ids = ids[2:]  # type: ignore[attr-defined]
        logger.info(
            "[BrowserLLM] primary=%s fallbacks=%s",
            ids[0],
            ",".join(ids[1:]),
        )
    return primary, fallback
