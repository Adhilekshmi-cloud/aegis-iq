import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "Aegis Knowledge System"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/aegis_knowledge.db"

    # CORS: supply as a plain string in Render
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        value = self.CORS_ORIGINS.strip()

        if not value:
            return []

        # Accept JSON array format
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