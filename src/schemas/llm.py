from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    query: str
    context_documents: list[str] = Field(default_factory=list)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    system_prompt: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    stream: bool = False


class LLMResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    provider: str
    model: str
    latency_ms: int | None = None
    usage: dict[str, int] | None = None