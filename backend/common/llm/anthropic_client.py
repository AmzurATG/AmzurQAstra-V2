"""
Anthropic LLM Client
"""
from typing import List, Optional
from anthropic import AsyncAnthropic

from common.llm.base import BaseLLMClient, Message, LLMResponse
from config import settings


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""
    
    def __init__(
        self, api_key: Optional[str] = None, default_model: str = "claude-3-opus-20240229"
    ):
        self.client = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.default_model = default_model
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send chat completion request to Anthropic."""
        model = model or self.default_model
        max_tokens = max_tokens or 4096
        
        # Extract system message if present
        system_content = None
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})
        
        kwargs = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_content:
            kwargs["system"] = system_content
        
        response = await self.client.messages.create(**kwargs)
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            } if response.usage else None,
        )
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate text from a single prompt."""
        messages = [Message(role="user", content=prompt)]
        return await self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
