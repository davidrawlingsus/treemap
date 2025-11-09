import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENV_FILE = PROJECT_ROOT / ".env.local"

if LOCAL_ENV_FILE.exists():
    load_dotenv(LOCAL_ENV_FILE, override=True)


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        extra = "ignore"
    database_url: str = "sqlite:///./treemap.db"
    database_public_url: str = ""
    environment: str = "development"
    jwt_secret_key: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7)  # 7 days
    magic_link_token_expire_minutes: int = Field(default=60)  # 60 minutes
    magic_link_rate_limit_seconds: int = Field(default=120)  # 2 minutes
    frontend_base_url: str = Field(default="http://localhost:3000")
    magic_link_redirect_path: str = Field(default="/magic-login")
    resend_api_key: str | None = Field(default=None)
    resend_from_email: str | None = Field(default=None)
    resend_reply_to_email: str | None = Field(default=None)
    google_oauth_client_id: str | None = Field(default=None)
    google_oauth_client_secret: str | None = Field(default=None)
    additional_cors_origins: str | None = Field(default=None)

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

    def get_additional_cors_origins(self) -> list[str]:
        value = self.additional_cors_origins
        if not value:
            return []

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [
                            str(origin).strip()
                            for origin in parsed
                            if str(origin).strip()
                        ]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in stripped.split(",") if item.strip()]

        if isinstance(value, (list, tuple, set)):
            return [str(origin).strip() for origin in value if str(origin).strip()]

        return []

@lru_cache()
def get_settings():
    return Settings()


