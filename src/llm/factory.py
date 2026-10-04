from llm.base import BaseLLM
from llm.vllm_client import VLLMClient
from llm.sglang_client import SGLangClient
from config import Config


def get_llm(config: Config) -> BaseLLM:
    if config.LLM_PROVIDER == "vllm":
        return VLLMClient(config)

    if config.LLM_PROVIDER == "sglang":
        return SGLangClient(config)

    raise ValueError("Unsupported LLM provider")