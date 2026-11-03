import json
from typing import List, Union

from pydantic import field_validator
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

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, value: Union[str, List[str], None]
    ) -> List[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [
                str(origin).strip()
                for origin in value
                if str(origin).strip()
            ]

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return []

            # Accept JSON format: ["https://example.com"]
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

            # Accept comma-separated origins
            return [
                origin.strip().strip('"').strip("'")
                for origin in value.split(",")
                if origin.strip().strip('"').strip("'")
            ]

        raise ValueError("CORS_ORIGINS must be a list or a string")


settings = Settings()