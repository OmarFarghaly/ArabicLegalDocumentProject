
import time
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from src.config import Config
from src.llm.base import BaseLLM
from src.schemas import LLMRequest, LLMResponse

from src.logger import Logger

logger = Logger().logger


class VLLMClient(BaseLLM):
    def __init__(self, config: Config):
        self.config = config
        try:
            self.client = AsyncOpenAI(
                    base_url=config.LLM_BASE_URL,
                    api_key=config.LLM_API_KEY,
                    timeout=config.LLM_TIMEOUT_SECONDS,
                )
        except Exception as e:
            logger.error(f"Error initializing VLLM client: {e}")
            raise

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()
        logger.info(f"Generating response for query: {request.query}")
        messages = []

        system_prompt = (
            request.system_prompt
            or self.config.LLM_SYSTEM_PROMPT
        )

        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        user_content = ""

        if request.chat_history:
            user_content += "Previous conversation:\n"
            for message in request.chat_history:
                user_content += (
                    f"{message.role}: {message.content}\n"
                )
            user_content += "\n"

        if request.context_documents:
            user_content += "Legal context:\n"
            for i, document in enumerate(
                request.context_documents, start=1
            ):
                user_content += f"[Document {i}]\n{document}\n\n"

        user_content += f"Current question:\n{request.query}"

        messages.append({
            "role": "user",
            "content": user_content,
        })

        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self.config.LLM_MAX_TOKENS
        )
        temperature = (
            request.temperature
            if request.temperature is not None
            else self.config.LLM_TEMPERATURE
        )
        top_p = (
            request.top_p if request.top_p is not None else self.config.LLM_TOP_P
        )
        repetition_penalty = (
            request.repetition_penalty
            if request.repetition_penalty is not None
            else self.config.LLM_REPETITION_PENALTY
        )
        logger.info(f"Sending request to VLLM with max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}, repetition_penalty={repetition_penalty}")
        response = await self.client.chat.completions.create(
            model=self.config.LLM_MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            extra_body={
                "repetition_penalty": repetition_penalty,
                "chat_template_kwargs": {
                    "enable_thinking": self.config.LLM_ENABLE_THINKING,
                },
            },
            stream=False,
        )

        answer = response.choices[0].message.content or ""
        logger.info(f"Received response from VLLM: {answer[:100]}...")  # Log first 100 characters of the answer

        latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        logger.info(f"Usage statistics for VLLM request: {usage}")

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
        logger.info(f"Generating stream response for query: {request.query}")
        messages = []
        system_prompt = (
            request.system_prompt
            or self.config.LLM_SYSTEM_PROMPT
        )

        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        user_content = ""

        if request.chat_history:
            user_content += "Previous conversation:\n"
            for message in request.chat_history:
                user_content += (
                    f"{message.role}: {message.content}\n"
                )
            user_content += "\n"

        if request.context_documents:
            user_content += "Legal context:\n"
            for i, document in enumerate(
                request.context_documents, start=1
            ):
                user_content += f"[Document {i}]\n{document}\n\n"

        user_content += f"Current question:\n{request.query}"

        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self.config.LLM_MAX_TOKENS
        )
        temperature = (
            request.temperature
            if request.temperature is not None
            else self.config.LLM_TEMPERATURE
        )
        top_p = (
            request.top_p if request.top_p is not None else self.config.LLM_TOP_P
        )
        repetition_penalty = (
            request.repetition_penalty
            if request.repetition_penalty is not None
            else self.config.LLM_REPETITION_PENALTY
        )
        logger.info(f"Sending streaming request to VLLM with max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}, repetition_penalty={repetition_penalty}")
        stream = await self.client.chat.completions.create(
            model=self.config.LLM_MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            extra_body={
                "repetition_penalty": repetition_penalty,
                "chat_template_kwargs": {
                    "enable_thinking": self.config.LLM_ENABLE_THINKING,
                },
            },
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content

            if content:
                yield content
        logger.info("Streaming response from VLLM completed.")

    async def health_check(self) -> bool:
        try:
            logger.info("Performing health check for VLLM client")
            await self.client.models.list()
            return True
        except Exception:
            logger.error("Health check failed for VLLM client")
            return False

    async def close(self) -> None:
        logger.info("Closing VLLM client")
        await self.client.close()
        logger.info("VLLM client closed successfully")