import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.llm.vllm_client import VLLMClient
from src.schemas.llm import LLMRequest


def make_client(response):
    config = SimpleNamespace(
        LLM_MODEL_NAME="test-model",
        LLM_MAX_NEW_TOKENS=128,
        LLM_TEMPERATURE=0.4,
        LLM_TOP_P=0.9,
        LLM_TOP_K=20,
        LLM_MIN_P=0.05,
        LLM_PRESENCE_PENALTY=1.5,
        LLM_REPETITION_PENALTY=1.1,
        LLM_ENABLE_THINKING=False,
        LLM_SYSTEM_PROMPT="Test system prompt",
    )
    client = VLLMClient.__new__(VLLMClient)
    client.config = config
    client.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=response))
        )
    )
    return client


def assert_sampling_options(kwargs):
    assert kwargs["temperature"] == 0.4
    assert kwargs["top_p"] == 0.9
    assert kwargs["presence_penalty"] == 1.5
    assert kwargs["extra_body"]["top_k"] == 20
    assert kwargs["extra_body"]["min_p"] == 0.05
    assert kwargs["extra_body"]["repetition_penalty"] == 1.1
    assert kwargs["extra_body"]["chat_template_kwargs"] == {
        "enable_thinking": False
    }


def test_generate_passes_config_sampling_parameters():
    async def run():
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
            usage=None,
        )
        client = make_client(response)

        result = await client.generate(LLMRequest(query="question"))

        kwargs = client.client.chat.completions.create.await_args.kwargs
        assert_sampling_options(kwargs)
        assert kwargs["max_tokens"] == 128
        assert kwargs["stream"] is False
        assert result.answer == "answer"

    asyncio.run(run())


def test_stream_generate_passes_config_sampling_parameters():
    async def run():
        class FakeStream:
            def __aiter__(self):
                async def chunks():
                    yield SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content="hi")
                            )
                        ]
                    )

                return chunks()

        client = make_client(FakeStream())

        chunks = [
            chunk
            async for chunk in client.stream_generate(
                LLMRequest(query="question")
            )
        ]

        kwargs = client.client.chat.completions.create.await_args.kwargs
        assert_sampling_options(kwargs)
        assert kwargs["max_tokens"] == 128
        assert kwargs["stream"] is True
        assert chunks == ["hi"]

    asyncio.run(run())
