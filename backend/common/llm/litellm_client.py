"""
LiteLLM Client - Unified interface supporting 100+ LLM providers

LiteLLM provides a unified API for OpenAI, Anthropic, Azure, Bedrock, 
Vertex AI, and many other LLM providers.
"""
from typing import List, Optional, Dict, Any, Tuple
import litellm
from litellm import acompletion, completion

from common.llm.base import BaseLLMClient, Message, LLMResponse
from common.utils.logger import logger
from config import settings


class LiteLLMClient(BaseLLMClient):
    """
    LiteLLM client for unified LLM access.
    
    Supports models from various providers:
    - OpenAI: gpt-4, gpt-3.5-turbo
    - Anthropic: claude-3-opus, claude-3-sonnet
    - Azure OpenAI: azure/gpt-4
    - AWS Bedrock: bedrock/anthropic.claude-3
    - Google Vertex AI: vertex_ai/gemini-pro
    - And many more...
    
    Model format: provider/model-name or just model-name for OpenAI
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """
        Initialize LiteLLM client.
        
        Args:
            api_key: API key for the LLM provider
            api_base: Base URL for custom deployments (e.g., LiteLLM proxy)
            default_model: Default model to use
        """
        self.api_key = api_key or settings.LITELLM_API_KEY
        self.api_base = api_base or settings.LITELLM_API_BASE
        self.default_model = default_model or settings.LITELLM_MODEL
        
        # Configure LiteLLM
        if self.api_key:
            litellm.api_key = self.api_key
        if self.api_base:
            litellm.api_base = self.api_base
        
        # Enable verbose logging in debug mode
        litellm.set_verbose = settings.DEBUG

    @staticmethod
    def _proxy_model_name(model: str, api_base: Optional[str]) -> str:
        """Prefix model with 'openai/' when routing through a LiteLLM proxy.

        When api_base is set (proxy mode), litellm's client-side routing
        sees prefixes like 'gemini/' and tries to call provider APIs directly
        instead of the proxy. Adding 'openai/' forces OpenAI-compatible
        routing through the proxy, which handles provider dispatch itself.
        """
        if api_base and not model.startswith("openai/"):
            return f"openai/{model}"
        return model

    def _model_attempts(self, primary: str) -> List[str]:
        """Ordered list: primary model, then comma-separated LITELLM_FALLBACK_MODELS (no duplicates)."""
        seen: set[str] = set()
        out: List[str] = []
        for m in [primary] + (
            [x.strip() for x in settings.LITELLM_FALLBACK_MODELS.split(",")]
            if settings.LITELLM_FALLBACK_MODELS
            else []
        ):
            if not m or m in seen:
                continue
            seen.add(m)
            out.append(m)
        return out

    def _completion_with_fallback(self, kwargs: Dict[str, Any]) -> Tuple[Any, str]:
        primary = kwargs.get("model") or self.default_model
        api_base = kwargs.get("api_base") or self.api_base
        last_exc: Optional[Exception] = None
        for model in self._model_attempts(primary):
            attempt = {**kwargs, "model": self._proxy_model_name(model, api_base)}
            try:
                response = completion(**attempt)
                if model != primary:
                    logger.info("LiteLLM completion succeeded with fallback model=%s", model)
                return response, model
            except Exception as e:
                last_exc = e
                logger.warning(
                    "LiteLLM completion failed for model=%s: %s",
                    model,
                    e,
                )
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LiteLLM completion failed with no model attempts")

    async def _acompletion_with_fallback(self, kwargs: Dict[str, Any]) -> Tuple[Any, str]:
        primary = kwargs.get("model") or self.default_model
        api_base = kwargs.get("api_base") or self.api_base
        last_exc: Optional[Exception] = None
        for model in self._model_attempts(primary):
            attempt = {**kwargs, "model": self._proxy_model_name(model, api_base)}
            try:
                response = await acompletion(**attempt)
                if model != primary:
                    logger.info("LiteLLM acompletion succeeded with fallback model=%s", model)
                return response, model
            except Exception as e:
                last_exc = e
                logger.warning(
                    "LiteLLM acompletion failed for model=%s: %s",
                    model,
                    e,
                )
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LiteLLM acompletion failed with no model attempts")

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send chat completion request via LiteLLM.
        
        Args:
            messages: List of chat messages
            model: Model to use (e.g., "gpt-4", "anthropic/claude-3-opus")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        
        Returns:
            LLMResponse with content and usage info
        """
        model = model or self.default_model
        
        # Convert messages to dict format
        messages_dict = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        # Prepare request kwargs
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages_dict,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        # Add API key and base if configured
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        response, model_used = await self._acompletion_with_fallback(kwargs)

        # Extract response content
        content = response.choices[0].message.content
        
        # Extract usage info
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=content,
            model=model_used,
            usage=usage,
        )

    def chat_sync(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send chat completion request via LiteLLM (synchronous).
        """
        model = model or self.default_model
        messages_dict = [{"role": m.role, "content": m.content} for m in messages]
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages_dict,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        response, model_used = self._completion_with_fallback(kwargs)

        content = response.choices[0].message.content
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            model=model_used,
            usage=usage,
        )

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text from a single prompt.
        
        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        
        Returns:
            LLMResponse with generated content
        """
        messages = [Message(role="user", content=prompt)]
        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    async def generate_json(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """
        Generate JSON response using response_format.
        
        Args:
            messages: List of chat messages
            model: Model to use
            temperature: Lower temperature for more deterministic output
        
        Returns:
            LLMResponse with JSON content
        """
        model = model or self.default_model
        
        messages_dict = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages_dict,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        response, model_used = await self._acompletion_with_fallback(kwargs)

        content = response.choices[0].message.content
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            model=model_used,
            usage=usage,
        )
