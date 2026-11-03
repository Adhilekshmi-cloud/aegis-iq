import json
import os
from pathlib import Path
from typing import List, Union

from pydantic_settings import BaseSettings, SettingsConfigDict


# Use a Windows-compatible database path locally and /tmp on Linux (Render).
DEFAULT_DATABASE_URL = (
    "sqlite+aiosqlite:////tmp/aegis_knowledge.db"
    if os.name != "nt"
    else f"sqlite+aiosqlite:///{(Path(__file__).resolve().parents[1] / 'aegis_knowledge.db').as_posix()}"
)

DEFAULT_DATA_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "aegis-dataset"
).as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Aegis Knowledge System"
    APP_VERSION: str = "1.0.0"
    PROJECT_NAME: str = "Aegis Knowledge System"
    API_V1_STR: str = "/api"
    DEBUG: bool = False

    # LLM & Embedding configuration
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Database
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    # Storage and paths
    DATA_DIR: str = DEFAULT_DATA_DIR
    LOG_LEVEL: str = "INFO"
    FAISS_INDEX_PATH: str = "./faiss_index"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS

        value = str(self.CORS_ORIGINS).strip()
        if not value:
            return ["*"]

        # Accept JSON array format, e.g. ["https://example.com"]
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [
                        str(origin).strip()
                        for origin in parsed
                        if str(origin).strip()
                    ]
            except json.JSONDecodeError:
                pass

        # Also accept comma-separated origins
        return [
            origin.strip().strip('"').strip("'")
            for origin in value.split(",")
            if origin.strip().strip('"').strip("'")
        ]


settings = Settings()
