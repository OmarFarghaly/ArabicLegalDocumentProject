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

    model_config = SettingsConfigDict(
        env_file=".env",
    )
        
# if __name__ == '__main__':
#     setting = Config()
    
#     print(setting.APP_NAME)
#     print(setting.ARABIC_EMBEDDING)
#     print(setting.ENGLISH_EMBEDDING)
    
    