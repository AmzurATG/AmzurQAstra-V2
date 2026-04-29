"""
LLM Client Service for Test Automation Engine

Provides a unified interface for LLM interactions supporting multiple providers
with LiteLLM as primary and automatic fallback to direct API calls.

This service is used by the Planner and Observer agents in the test automation engine.
"""

import os
import logging
import json
import httpx
from typing import List, Dict, Any, Optional

# Make dotenv import optional - env vars may already be loaded by parent process
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Environment variables should already be set by main application

# Configure logging
logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass


class LLMClient:
    """
    LLM Client with support for multiple providers.
    
    Supports (in order of preference):
    - LiteLLM Proxy (Primary)
    - Direct OpenAI API (Fallback)
    - Fireworks AI (Fallback)
    
    Features:
    - Automatic provider fallback
    - JSON response parsing
    - Streaming support
    - Error handling and retries
    """
    
    def __init__(self, use_fireworks: bool = False):
        """
        Initialize LLM Client.
        
        Args:
            use_fireworks: Whether to prefer Fireworks AI over OpenAI
        """
        # LiteLLM configuration (Primary)
        self.litellm_openai_key = os.getenv("LITELLM_OPENAI_API_KEY")
        self.litellm_proxy_url = os.getenv("LITELLM_PROXY_URL", "https://litellm.amzur.com")
        self.user_email = os.getenv("USER_EMAIL", "qastra.dev@amzur.com")
        
        # OpenAI configuration (Fallback)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Use gpt-4o-mini as default
        
        # Fireworks AI configuration (Fallback)
        self.fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
        self.fireworks_model = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-70b-instruct")
        
        # Provider preference
        self.use_fireworks = use_fireworks
        self.current_provider = None
        
        # Validate at least one provider is configured
        has_litellm = bool(self.litellm_openai_key)
        has_fallback = bool(self.openai_api_key or self.fireworks_api_key)
        
        if not has_litellm and not has_fallback:
            raise LLMError("No LLM provider configured. Set LITELLM_OPENAI_API_KEY, OPENAI_API_KEY or FIREWORKS_API_KEY.")
        
        logger.info(
            f"LLM Client initialized - "
            f"LiteLLM: {'configured' if self.litellm_openai_key else 'not configured'}, "
            f"OpenAI: {'configured' if self.openai_api_key else 'not configured'}, "
            f"Fireworks: {'configured' if self.fireworks_api_key else 'not configured'}"
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 60.0
    ) -> str:
        """
        Get a chat completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            Response text from the LLM
            
        Raises:
            LLMError: If all providers fail
        """
        # Try LiteLLM first (Primary)
        if self.litellm_openai_key:
            try:
                return await self._litellm_completion(messages, temperature, max_tokens, timeout)
            except Exception as e:
                logger.warning(f"LiteLLM failed: {e}. Falling back to direct APIs.")
        
        # Try preferred provider first (if Fireworks is preferred)
        if self.use_fireworks and self.fireworks_api_key:
            try:
                return await self._fireworks_completion(messages, temperature, max_tokens, timeout)
            except Exception as e:
                logger.warning(f"Fireworks AI failed: {e}. Falling back to OpenAI.")
                if self.openai_api_key:
                    return await self._openai_completion(messages, temperature, max_tokens, timeout)
                raise LLMError(f"Fireworks AI failed and no OpenAI fallback: {e}")
        
        # Try direct OpenAI (Fallback)
        if self.openai_api_key:
            try:
                return await self._openai_completion(messages, temperature, max_tokens, timeout)
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}. Falling back to Fireworks AI.")
                if self.fireworks_api_key:
                    return await self._fireworks_completion(messages, temperature, max_tokens, timeout)
                raise LLMError(f"OpenAI failed and no Fireworks AI fallback: {e}")
        
        # Only Fireworks available
        if self.fireworks_api_key:
            return await self._fireworks_completion(messages, temperature, max_tokens, timeout)
        
        raise LLMError("No LLM provider available")
    
    async def chat_completion_with_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Get a chat completion and parse as JSON.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            Parsed JSON response
            
        Raises:
            LLMError: If completion fails or response is not valid JSON
        """
        response_text = await self.chat_completion(messages, temperature, max_tokens, timeout)
        
        try:
            # Try to find JSON in the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            
            # Try parsing the whole response as JSON
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response_text[:200]}")
            raise LLMError(f"Invalid JSON in LLM response: {e}")
    
    async def _litellm_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call OpenAI via LiteLLM proxy (Primary)."""
        url = f"{self.litellm_proxy_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.litellm_openai_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.openai_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "user": self.user_email
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Log the LiteLLM API call
                try:
                    from .universal_llm_logger import log_openai_call
                    log_openai_call(f"litellm-{self.openai_model}", messages, result)
                except Exception as e:
                    logger.warning(f"Failed to log LiteLLM API call: {e}")
                
                self.current_provider = "litellm"
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"LiteLLM response: {content[:100]}...")
                
                # Log token usage
                if "usage" in result:
                    logger.info(f"LiteLLM tokens used: {result['usage'].get('total_tokens', 0)}")
                
                return content
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if hasattr(e, 'response') else str(e)
                logger.error(f"LiteLLM API error: {error_detail}")
                raise LLMError(f"LiteLLM API error: {error_detail}")
            except Exception as e:
                logger.error(f"LiteLLM request failed: {e}")
                raise LLMError(f"LiteLLM request failed: {e}")
    
    async def _openai_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call OpenAI API directly (Fallback)."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # GPT-4o and newer models use max_completion_tokens, older models use max_tokens
        # Note: gpt-4o-mini uses max_tokens (legacy parameter)
        token_param = "max_tokens"
        if "gpt-4o" in self.openai_model and "mini" not in self.openai_model:
            token_param = "max_completion_tokens"
        
        # Build request data
        data = {
            "model": self.openai_model,
            "messages": messages,
            token_param: max_tokens,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Log the OpenAI API call
                try:
                    from .universal_llm_logger import log_openai_call
                    log_openai_call(self.openai_model, messages, result)
                except Exception as e:
                    logger.warning(f"Failed to log OpenAI API call: {e}")
                
                self.current_provider = "openai"
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"OpenAI response: {content[:100]}...")
                return content
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if hasattr(e, 'response') else str(e)
                logger.error(f"OpenAI API error: {error_detail}")
                raise LLMError(f"OpenAI API error: {error_detail}")
            except Exception as e:
                logger.error(f"OpenAI request failed: {e}")
                raise LLMError(f"OpenAI request failed: {e}")
    
    async def _fireworks_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call Fireworks AI API."""
        url = "https://api.fireworks.ai/inference/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.fireworks_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.fireworks_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                self.current_provider = "fireworks"
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"Fireworks AI response: {content[:100]}...")
                return content
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if hasattr(e, 'response') else str(e)
                logger.error(f"Fireworks AI API error: {error_detail}")
                raise LLMError(f"Fireworks AI API error: {error_detail}")
            except Exception as e:
                logger.error(f"Fireworks AI request failed: {e}")
                raise LLMError(f"Fireworks AI request failed: {e}")


def get_llm_client(use_fireworks: bool = False) -> LLMClient:
    """
    Factory function to get an LLM client instance.
    
    Args:
        use_fireworks: Whether to prefer Fireworks AI over OpenAI
        
    Returns:
        LLMClient instance
    """
    return LLMClient(use_fireworks=use_fireworks)
