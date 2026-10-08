import time
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from config import Config
from llm.base import BaseLLM
from schemas.llm import LLMRequest, LLMResponse


class VLLMClient(BaseLLM):
    def __init__(self, config: Config):
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
            timeout=config.LLM_TIMEOUT_SECONDS,
        )

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        system_prompt = (
            request.system_prompt
            if request.system_prompt is not None
            else self.config.LLM_SYSTEM_PROMPT
        )

        user_content = ""

        if request.chat_history:
            user_content += "Previous conversation:\n"
            for message in request.chat_history:
                user_content += f"{message.role}: {message.content}\n"
            user_content += "\n"

        if request.context_documents:
            user_content += "Legal context:\n"
            for i, document in enumerate(request.context_documents, start=1):
                user_content += f"[Document {i}]\n{document}\n\n"

        user_content += f"Current question:\n{request.query}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _generation_options(self, request: LLMRequest) -> dict:
        return {
            "model": self.config.LLM_MODEL_NAME,
            "messages": self._build_messages(request),
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self.config.LLM_MAX_TOKENS
            ),
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self.config.LLM_TEMPERATURE
            ),
            "top_p": (
                request.top_p
                if request.top_p is not None
                else self.config.LLM_TOP_P
            ),
            #"extra_body": {
            #    "repetition_penalty": (
            #        request.repetition_penalty
            #        if request.repetition_penalty is not None
            #        else self.config.LLM_REPETITION_PENALTY
            #    ),
            #},
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()

        response = await self.client.chat.completions.create(
            **self._generation_options(request),
            stream=False,
        )

        answer = response.choices[0].message.content or ""
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            answer=answer,
            sources=request.context_documents,
            provider="vllm",
            model=self.config.LLM_MODEL_NAME,
            latency_ms=latency_ms,
            usage=usage,
        )

    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            **self._generation_options(request),
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self.client.close()