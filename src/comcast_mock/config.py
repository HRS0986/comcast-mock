import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into the process environment so individual PG* params (as exported
# from the Neon dashboard) are available. Only a fallback when DATABASE_URL is
# not set directly.
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_ROOT / ".env", override=False)
load_dotenv(override=False)

# sslmode values that require an encrypted connection (libpq terminology).
_SSLMODES_REQUIRING_SSL = {"require", "verify-ca", "verify-full"}


def _resolve_database_url() -> str:
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit

    host = os.environ.get("PGHOST")
    user = os.environ.get("PGUSER")
    password = os.environ.get("PGPASSWORD")
    database = os.environ.get("PGDATABASE", "postgres")

    if host and user and password:
        return f"postgresql+asyncpg://{user}:{password}@{host}/{database}"

    # Local dev fallback (no external DB configured).
    return "sqlite+aiosqlite:///comcast_mock.db"


def _resolve_connect_args() -> dict[str, Any]:
    # An explicitly-provided DATABASE_URL is used verbatim (the driver/params are
    # the caller's responsibility, e.g. postgresql+psycopg://...?sslmode=require).
    if os.environ.get("DATABASE_URL"):
        return {}

    sslmode = (os.environ.get("PGSSLMODE") or "").lower()
    if sslmode in _SSLMODES_REQUIRING_SSL:
        # asyncpg negotiates TLS and verifies the server certificate+hostname.
        return {"ssl": True}
    return {}


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
    database_url: str = _resolve_database_url()
    connect_args: dict[str, Any] = _resolve_connect_args()

    default_limit: int = 50
    max_limit: int = 200
    frontend_url: str = "http://localhost:3000"


settings = Settings()
