"""
Base LLM Interface
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel


class Message(BaseModel):
    """Chat message."""
    role: str  # "system", "user", "assistant"
    # str for text; list of parts for multimodal / vision (OpenAI-compatible)
    content: Union[str, List[Dict[str, Any]]]


class LLMResponse(BaseModel):
    """LLM response."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send chat completion request."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate text from a single prompt."""
        pass

    @abstractmethod
    def chat_sync(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send chat completion request (synchronous)."""
        pass
    
    def chat_with_system_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Convenience method for chat with system prompt (synchronous)."""
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        return self.chat_sync(messages, model=model, temperature=temperature)

    async def chat_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Convenience method for chat with system prompt."""
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        return await self.chat(messages, model=model, temperature=temperature)
