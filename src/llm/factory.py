
from llm.base import BaseLLM
#from llm.sglang_client import SGLangClient
from src.config import Config
from src.llm.base import BaseLLM
from src.llm.vllm_client import VLLMClient
from src.logger import Logger

logger = Logger().logger


def get_llm(config: Config) -> BaseLLM:
    if config.LLM_PROVIDER == "vllm":
        logger.info("Initializing VLLM client")
        return VLLMClient(config)

        #if config.LLM_PROVIDER == "sglang":
        #return SGLangClient(config)

        raise ValueError("Unsupported LLM provider")
    else:
        logger.error("Unsupported LLM provider")
        raise ValueError("Unsupported LLM provider")
