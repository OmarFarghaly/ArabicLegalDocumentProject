from src.config import Config
from src.llm.base import BaseLLM
from src.llm.vllm_client import VLLMClient
from src.logger import Logger

logger = Logger().logger


def get_llm(config: Config) -> BaseLLM:
    if config.LLM_PROVIDER == "vllm":
        logger.info("Initializing VLLM client")
        return VLLMClient(config)
    else:
        logger.error("Unsupported LLM provider")
        raise ValueError("Unsupported LLM provider")