from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Config(BaseSettings):
    
    APP_NAME:str = Field(min_length=3, max_length=100)
    ENGLISH_EMBEDDING:str
    ARABIC_EMBEDDING:str
    COLLECTION_NAME:str
    
    RAW_PDF: str
    ARTICLES_JSON: str

    VALIDATE_SCHEMA: bool = True
    ENSURE_ASCII: bool = False
    INDENT: int = 2

    LLM_PROVIDER: str = "vllm"
    LLM_MODEL_NAME: str = "" #NOT YET SET
    LLM_BASE_URL: str = "http://localhost:12434/engines/v1"
    LLM_API_KEY: str = "EMPTY"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_TOKENS: int = 512
    LLM_TEMPERATURE: float = 0.2
    LLM_TOP_P: float = 0.95
    LLM_REPETITION_PENALTY: float = 1.05
    LLM_STREAMING_ENABLED: bool = True
    LLM_SYSTEM_PROMPT: str = "You are a legal assistant. Answer using only the provided legal context. If the answer is not supported by the retrieved legal documents, say so clearly."
    LLM_MAX_CONTEXT_DOCS: int = 5
    LLM_MAX_CONTEXT_CHARS: int = 12000
    LLM_RETRY_COUNT: int = 2
    LLM_RETRY_BACKOFF_SECONDS: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
    )
        
# if __name__ == '__main__':
#     setting = Config()
    
#     print(setting.APP_NAME)
#     print(setting.ARABIC_EMBEDDING)
#     print(setting.ENGLISH_EMBEDDING)
    
    