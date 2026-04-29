"""
LiteLLM Client Service for QAstra

Provides a unified interface for LLM interactions using LiteLLM proxy 
as the primary method with fallback to direct API calls.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional

# Make dotenv import optional - env vars may already be loaded by parent process
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Environment variables should already be set by main application

# Configure logging
logger = logging.getLogger(__name__)

class LiteLLMClient:
    """
    LiteLLM Client with fallback to direct API access.
    
    Features:
    - Primary: LiteLLM proxy for unified access
    - Fallback: Direct OpenAI and Gemini API calls
    - Automatic provider fallback
    - JSON response parsing
    - Error handling and retries
    """
    
    def __init__(self):
        """Initialize LiteLLM Client with fallback configuration."""
        
        # LiteLLM configuration (Primary)
        self.litellm_openai_key = os.getenv("LITELLM_OPENAI_API_KEY")
        self.litellm_google_key = os.getenv("LITELLM_GOOGLE_API_KEY") 
        self.litellm_proxy_url = os.getenv("LITELLM_PROXY_URL", "https://litellm.amzur.com")
        self.user_email = os.getenv("USER_EMAIL", "qastra.dev@amzur.com")
        
        # Fallback configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Model configurations
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # Use different model naming for LiteLLM proxy vs direct API
        self.gemini_model_litellm = os.getenv("GEMINI_MODEL_LITELLM", "gemini/gemini-2.0-flash") 
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
        # Track current provider (for compatibility)
        self.current_provider = "litellm"  # Default to litellm
        self.fireworks_model = self.openai_model  # For compatibility
        
        # Validate configuration
        has_litellm = bool(self.litellm_openai_key or self.litellm_google_key)
        has_fallback = bool(self.openai_api_key or self.gemini_api_key)
        
        if not has_litellm and not has_fallback:
            raise Exception("No LLM provider configured. Set LiteLLM keys or fallback API keys.")
            
        self.current_provider = None
        
        logger.info(
            f"LiteLLM Client initialized - "
            f"LiteLLM OpenAI: {'configured' if self.litellm_openai_key else 'not configured'}, "
            f"LiteLLM Google: {'configured' if self.litellm_google_key else 'not configured'}, "
            f"Fallback OpenAI: {'configured' if self.openai_api_key else 'not configured'}, "
            f"Fallback Gemini: {'configured' if self.gemini_api_key else 'not configured'}"
        )
    
    async def chat_completion_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 60.0
    ) -> str:
        """
        Get OpenAI chat completion with LiteLLM primary, direct API fallback.
        """
        # Try LiteLLM first
        if self.litellm_openai_key:
            try:
                return await self._litellm_openai_completion(messages, temperature, max_tokens, timeout)
            except Exception as e:
                logger.warning(f"LiteLLM OpenAI failed: {e}. Falling back to direct OpenAI API.")
                
        # Fallback to direct OpenAI API
        if self.openai_api_key:
            return await self._direct_openai_completion(messages, temperature, max_tokens, timeout)
            
        raise Exception("No OpenAI provider available")
    
    async def chat_completion_gemini(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 60.0
    ) -> str:
        """
        Get Gemini chat completion with LiteLLM primary, direct API fallback.
        """
        # Try LiteLLM first
        if self.litellm_google_key:
            try:
                return await self._litellm_gemini_completion(messages, temperature, max_tokens, timeout)
            except Exception as e:
                logger.warning(f"LiteLLM Gemini failed: {e}. Falling back to direct Gemini API.")
                
        # Fallback to direct Gemini API
        if self.gemini_api_key:
            return await self._direct_gemini_completion(messages, temperature, max_tokens, timeout)
            
        raise Exception("No Gemini provider available")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 60.0
    ) -> str:
        """
        Generic chat completion method that tries OpenAI first, then Gemini.
        
        Args:
            messages: List of message dictionaries
            temperature: Temperature for response generation
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            String response from the LLM
        """
        try:
            # Try OpenAI first
            return await self.chat_completion_openai(messages, temperature, max_tokens, timeout)
        except Exception as e:
            logger.warning(f"OpenAI completion failed: {e}. Trying Gemini...")
            # Fallback to Gemini
            return await self.chat_completion_gemini(messages, temperature, max_tokens, timeout)
    
    async def chat_completion_with_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 60.0
    ) -> str:
        """
        Chat completion method optimized for JSON responses.
        
        Args:
            messages: List of message dictionaries
            temperature: Temperature for response generation
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            String response from the LLM (should be JSON format)
        """
        # Add instruction for JSON response
        if messages and len(messages) > 0:
            system_msg = "Please respond with valid JSON format."
            # Check if there's already a system message
            if messages[0].get("role") == "system":
                messages[0]["content"] = f"{messages[0]['content']}\n\n{system_msg}"
            else:
                messages.insert(0, {"role": "system", "content": system_msg})
        
        return await self.chat_completion(messages, temperature, max_tokens, timeout)
    
    async def _litellm_openai_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call OpenAI via LiteLLM proxy."""
        import httpx
        
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
                response = await client.post(
                    f"{self.litellm_proxy_url}/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                # Log the API call
                try:
                    from .universal_llm_logger import log_openai_call
                    log_openai_call(self.openai_model, messages, result)
                except Exception as e:
                    logger.warning(f"Failed to log LiteLLM OpenAI API call: {e}")
                
                self.current_provider = "litellm_openai"
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"LiteLLM OpenAI response: {content[:100]}...")
                
                # Log token usage
                if "usage" in result:
                    logger.info(f"LiteLLM OpenAI tokens used: {result['usage'].get('total_tokens', 0)}")
                
                return content
                
            except Exception as e:
                logger.error(f"LiteLLM OpenAI request failed: {e}")
                raise Exception(f"LiteLLM OpenAI request failed: {e}")
    
    async def _litellm_gemini_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call Gemini via LiteLLM proxy."""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.litellm_google_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.gemini_model_litellm,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "user": self.user_email
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    f"{self.litellm_proxy_url}/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                self.current_provider = "litellm_gemini"
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"LiteLLM Gemini response: {content[:100]}...")
                
                # Log token usage
                if "usage" in result:
                    logger.info(f"LiteLLM Gemini tokens used: {result['usage'].get('total_tokens', 0)}")
                
                return content
                
            except Exception as e:
                logger.error(f"LiteLLM Gemini request failed: {e}")
                raise Exception(f"LiteLLM Gemini request failed: {e}")
    
    async def _direct_openai_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call OpenAI API directly (fallback)."""
        import httpx
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.openai_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Log the API call
                try:
                    from .universal_llm_logger import log_openai_call
                    log_openai_call(self.openai_model, messages, result)
                except Exception as e:
                    logger.warning(f"Failed to log direct OpenAI API call: {e}")
                
                self.current_provider = "direct_openai"
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"Direct OpenAI response: {content[:100]}...")
                
                # Log the API call to Excel sheet
                try:
                    from .universal_llm_logger import log_openai_call
                    log_openai_call(self.openai_model, messages, result)
                except Exception as e:
                    logger.warning(f"Failed to log direct OpenAI API call: {e}")
                
                return content
                
            except Exception as e:
                logger.error(f"Direct OpenAI request failed: {e}")
                raise Exception(f"Direct OpenAI request failed: {e}")
    
    async def _direct_gemini_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> str:
        """Call Gemini API directly (fallback)."""
        import google.generativeai as genai
        
        try:
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(self.gemini_model)
            
            # Convert OpenAI format to Gemini format
            prompt_parts = []
            for message in messages:
                role = "user" if message["role"] in ["user", "system"] else "assistant"
                prompt_parts.append(f"{role}: {message['content']}")
            
            prompt = "\n".join(prompt_parts)
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            
            self.current_provider = "direct_gemini"
            content = response.text
            logger.debug(f"Direct Gemini response: {content[:100]}...")
            
            # Log the API call to Excel sheet
            try:
                from .universal_llm_logger import log_gemini_call
                log_gemini_call(self.gemini_model, prompt, response)
            except Exception as e:
                logger.warning(f"Failed to log direct Gemini API call: {e}")
            
            return content
            
        except Exception as e:
            logger.error(f"Direct Gemini request failed: {e}")
            raise Exception(f"Direct Gemini request failed: {e}")


def get_sync_gemini_response(prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    Synchronous wrapper for Gemini responses using LiteLLM with fallback.
    """
    import asyncio
    
    async def _async_call():
        client = LiteLLMClient()
        messages = [{"role": "user", "content": prompt}]
        return await client.chat_completion_gemini(messages, temperature, max_tokens)
    
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _async_call())
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(_async_call())
    except Exception:
        # If no loop or other issues, create new one
        return asyncio.run(_async_call())

def get_litellm_client() -> LiteLLMClient:
    """
    Factory function to get a LiteLLM client instance.
    
    Returns:
        LiteLLMClient instance
    """
    return LiteLLMClient()