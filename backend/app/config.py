from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    database_url: str = "sqlite:///./treemap.db"
    database_public_url: str = ""
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    def get_database_url(self) -> str:
        """
        Get the appropriate database URL.
        Prefers DATABASE_PUBLIC_URL for local development (external access).
        Falls back to DATABASE_URL (internal Railway URL).
        """
        # Check environment variable first (highest priority)
        public_url = os.getenv('DATABASE_PUBLIC_URL') or self.database_public_url
        internal_url = os.getenv('DATABASE_URL') or self.database_url
        
        # Prefer public URL if available (for local development)
        if public_url:
            return public_url
        
        # Fall back to internal URL (for Railway deployment)
        return internal_url


@lru_cache()
def get_settings():
    return Settings()


