from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Kaya CX Triage Backend"
    app_version: str = "0.1.0"
    debug: bool = False

    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///comcast_mock.db"

    default_limit: int = 50
    max_limit: int = 200

    frontend_url: str = "http://localhost:3000"


settings = Settings()
