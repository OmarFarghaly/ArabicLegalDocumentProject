from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from schemas.llm import LLMRequest, LLMResponse


class BaseLLM(ABC):

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass