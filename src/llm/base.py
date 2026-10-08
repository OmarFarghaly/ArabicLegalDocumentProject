from abc import ABC, abstractmethod

from llm.model import LLMResponse
from llm.model import LLMRequest


class BaseLLM(ABC):

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    def stream_generate(self, request: LLMRequest):
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass