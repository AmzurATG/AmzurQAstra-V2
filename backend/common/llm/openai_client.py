"""
OpenAI LLM Client
"""
from typing import List, Optional
from openai import AsyncOpenAI

from common.llm.base import BaseLLMClient, Message, LLMResponse
from config import settings


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: Optional[str] = None, default_model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.default_model = default_model
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send chat completion request to OpenAI."""
        model = model or self.default_model
        
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        kwargs = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
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
