"""
LLM factory for browser-use: LiteLLM proxy (default) or direct Google Gemini.

For a LiteLLM **OpenAI-compatible** proxy, we use ChatOpenAI (AsyncOpenAI
``/v1/chat/completions``). Do not use ChatLiteLLM here for ``gemini/...`` models:
litellm will treat them as provider ``gemini`` and call Google's API shape,
which against a proxy URL yields errors like ``405 Method Not Allowed``.

Vision: use a vision-capable model id on the proxy (e.g. gemini/gemini-2.5-flash)
and Agent(use_vision=True).
"""
from __future__ import annotations

from typing import Any

from config import settings


def _build_gated_openai_class():
    """Subclass browser-use ChatOpenAI so every ainvoke passes through the shared
    resilience gate (rate limit + circuit breaker + timeout). ChatOpenAI is a
    dataclass, so a plain method-override subclass keeps full compatibility
    (isinstance(BaseChatModel) still holds)."""
    from browser_use import ChatOpenAI
    from features.functional.core.browser.llm_gate import get_gate

    class GatedChatOpenAI(ChatOpenAI):  # type: ignore[misc]
        async def ainvoke(self, messages: Any, output_format: Any = None, **kwargs: Any):  # type: ignore[override]
            gate = get_gate()
            return await gate.call(
                lambda: super(GatedChatOpenAI, self).ainvoke(messages, output_format, **kwargs)
            )

    return GatedChatOpenAI


def get_browser_use_llm(model_override: str | None = None):
    """
    Return a browser-use chat model (BaseChatModel).

    Default: ChatOpenAI with LITELLM_API_BASE + virtual key (same as OpenAI SDK tests).

    Optional: BROWSER_USE_LLM_BACKEND=google → ChatGoogle + GEMINI_API_KEY.

    Args:
        model_override: Explicit model id (e.g. vision-retry model). Prefer this
            over mutating the global BROWSER_USE_LLM_MODEL env — it is safe under
            concurrent lanes.
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
        return ChatGoogle(
            model=model,
            api_key=settings.GEMINI_API_KEY.strip(),
            temperature=settings.BROWSER_USE_LLM_TEMPERATURE,
        )

    if not settings.LITELLM_API_KEY or not settings.LITELLM_API_BASE:
        raise ValueError(
            "Browser agent uses LiteLLM proxy by default. Set LITELLM_API_KEY and LITELLM_API_BASE "
            "(include /v1 in the base URL), and a vision-capable LITELLM_MODEL. "
            "Or set BROWSER_USE_LLM_BACKEND=google with GEMINI_API_KEY."
        )

    gated_cls = _build_gated_openai_class()
    model = override or (settings.BROWSER_USE_LLM_MODEL or settings.LITELLM_MODEL).strip()
    base = settings.LITELLM_API_BASE.strip().rstrip("/")
    # browser-use defaults frequency_penalty=0.3; Gemini rejects penalty params (400).
    # max_retries kept low: the shared gate + case-level retry own resilience, so
    # we don't want the HTTP client silently retrying 429s 5x and amplifying load
    # (and budget-400s are non-retryable anyway).
    return gated_cls(
        model=model,
        api_key=settings.LITELLM_API_KEY.strip(),
        base_url=base,
        temperature=settings.BROWSER_USE_LLM_TEMPERATURE,
        frequency_penalty=None,
        max_retries=2,
    )
