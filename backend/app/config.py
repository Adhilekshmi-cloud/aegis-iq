"""Configuration management for the Aegis Knowledge System backend."""

import logging
from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application info
    APP_NAME: str = "Aegis Knowledge System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LLM & Embedding configuration
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Database configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./aegis_knowledge.db"

    # CORS configuration
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # Storage and paths
    DATA_DIR: str = "../data/aegis-dataset"
    LOG_LEVEL: str = "INFO"
    FAISS_INDEX_PATH: str = "./faiss_index"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Allow CORS_ORIGINS to be a comma-separated string or list."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()

# Setup logging configuration
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegis")
