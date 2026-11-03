import json
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


# Use a Windows-compatible database path locally and /tmp on Linux (Render).
DEFAULT_DATABASE_URL = (
    "sqlite+aiosqlite:////tmp/aegis_knowledge.db"
    if os.name != "nt"
    else f"sqlite+aiosqlite:///{(Path(__file__).resolve().parents[1] / 'aegis_knowledge.db').as_posix()}"
)


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
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    # CORS
    # Set this in Render as a plain string, e.g.:
    # https://your-frontend-name.onrender.com
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        value = self.CORS_ORIGINS.strip()

        if not value:
            return []

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