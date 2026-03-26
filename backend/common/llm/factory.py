"""
LLM Client Factory
"""
from typing import Optional
from common.llm.base import BaseLLMClient
from common.llm.openai_client import OpenAIClient
from common.llm.anthropic_client import AnthropicClient
from common.llm.litellm_client import LiteLLMClient
from config import settings


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLMClient:
    """
    Get LLM client based on provider.

    Supported providers:
    - "openai"   — direct OpenAI API
    - "anthropic" — direct Anthropic API
    - "litellm"  — unified proxy (default)
    - "gemini"   — Google Gemini via LiteLLM (uses GEMINI_API_KEY)
    """
    provider = provider or settings.DEFAULT_LLM_PROVIDER

    if provider == "openai":
        return OpenAIClient(default_model=model or settings.DEFAULT_LLM_MODEL)
    elif provider == "anthropic":
        return AnthropicClient(default_model=model or "claude-3-opus-20240229")
    elif provider == "litellm":
        return LiteLLMClient(default_model=model or settings.LITELLM_MODEL)
    elif provider == "gemini":
        return LiteLLMClient(
            api_key=settings.GEMINI_API_KEY,
            api_base=None,
            default_model=model or "gemini/gemini-2.0-flash",
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
