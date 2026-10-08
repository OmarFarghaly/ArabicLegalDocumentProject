from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class LLMRequest:
    query: str
    context_documents: list[str] = field(default_factory=list)
    chat_history: list[ChatMessage] = field(default_factory=list)
    system_prompt: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    stream: bool = False


@dataclass
class LLMResponse:
    answer: str
    sources: list[str] = field(default_factory=list)
    provider: str
    model: str
    latency_ms: int | None = None
    usage: dict[str, Any] | None = None