from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    
    APP_NAME:str = Field(min_length=3, max_length=100)
    ENGLISH_EMBEDDING:str
    ARABIC_EMBEDDING:str
    RERANKER_MODEL:str
    COLLECTION_NAME:str
    
    RETERIVAL_LIMIT:int
    RETERIVAL_RRF_LIMIT:int
    RETERIVAL_RERANKED_LIMIT:int   
    
    RAW_PDF: str
    ARTICLES_JSON: str

    VALIDATE_SCHEMA: bool = True
    ENSURE_ASCII: bool = False
    INDENT: int = 2

    LLM_PROVIDER: str = "vllm"
    LLM_MODEL_NAME: str = ""
    LLM_MODEL_NAME: str = "" #NOT YET SET
    LLM_BASE_URL: str = "http://localhost:8000/v1"
    LLM_API_KEY: str = "EMPTY"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.2
    LLM_TOP_P: float = 0.95
    LLM_REPETITION_PENALTY: float = 1.05
    LLM_ENABLE_THINKING: bool = False
    LLM_STREAMING_ENABLED: bool = True
    LLM_SYSTEM_PROMPT: str = (
        "You are a legal assistant. Answer using only the provided legal context. "
        "If the answer is unsupported, say so clearly. Use the same language "
        "as the user's query, Arabic or English."
    )
    LLM_MAX_CONTEXT_DOCS: int = 5
    LLM_MAX_CONTEXT_CHARS: int = 12000
    LLM_RETRY_COUNT: int = 2
    LLM_RETRY_BACKOFF_SECONDS: int = 2
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    # Cache Configuration
    CACHE_ENABLED: bool = True
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CACHE_TTL_SECONDS: int = 3600
    SEMANTIC_CACHE_THRESHOLD: float = 0.12


    model_config = SettingsConfigDict(
        env_file=".env",
    )
        
# if __name__ == '__main__':
#     setting = Config()
    
#     print(setting.APP_NAME)
#     print(setting.ARABIC_EMBEDDING)
#     print(setting.ENGLISH_EMBEDDING)
    
    
