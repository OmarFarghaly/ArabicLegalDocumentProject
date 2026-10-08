# src/llm/providers/vllm_client.py

import time
from collections.abc import Generator

from openai import OpenAI

from src.config import Config
from src.llm.base import BaseLLM
from src.schemas import LLMRequest, LLMResponse


class VLLMClient(BaseLLM):
    def __init__(self, config: Config):
        self.config = config

        self.client = OpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
            timeout=config.LLM_TIMEOUT_SECONDS,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()

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
            or self.config.LLM_MAX_TOKENS
        )
        temperature = (
            request.temperature
            or self.config.LLM_TEMPERATURE
        )
        top_p = request.top_p or self.config.LLM_TOP_P
        repetition_penalty = (
            request.repetition_penalty
            or self.config.LLM_REPETITION_PENALTY
        )

        response = self.client.chat.completions.create(
            #Create a chat completion
            #using this model
            #with these messages
            #and these generation settings

            model=self.config.LLM_MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            extra_body={
                "repetition_penalty": repetition_penalty,
            },
            stream=False,
        )

        answer = response.choices[0].message.content or ""

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

        return LLMResponse(
            answer=answer,
            sources=request.context_documents,
            provider="vllm",
            model=self.config.LLM_MODEL_NAME,
            latency_ms=latency_ms,
            usage=usage,
        )

    def stream_generate(
        self,
        request: LLMRequest,
    ) -> Generator[str, None, None]:
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
            or self.config.LLM_MAX_TOKENS
        )
        temperature = (
            request.temperature
            or self.config.LLM_TEMPERATURE
        )
        top_p = request.top_p or self.config.LLM_TOP_P
        repetition_penalty = (
            request.repetition_penalty
            or self.config.LLM_REPETITION_PENALTY
        )

        stream = self.client.chat.completions.create(
            model=self.config.LLM_MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            extra_body={
                "repetition_penalty": repetition_penalty,
            },
            stream=True,
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content

            if content:
                yield content

    def health_check(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def close(self) -> None:
        self.client.close()