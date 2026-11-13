from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HopLogic BrauPartner"
    environment: str = "development"
    database_url: str
    cors_origins: str = "http://localhost:5173"
    ticket_upload_dir: str = "data/ticket-attachments"
    ticket_max_bytes: int = 5_242_880
    automation_embedded_worker: bool = True
    automation_interval_seconds: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
