from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    environment: str = "development"
    
    # OpenAI Configuration (optional - only needed for Growth Ideas feature)
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = "gpt-3.5-turbo"
    openai_max_ideas: Optional[int] = 8
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


