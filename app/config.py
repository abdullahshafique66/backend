from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Apna Hisab Kitaab API"
    # SQLite by default (zero setup). For PostgreSQL:
    #   DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/apna_hisab
    database_url: str = "sqlite:///./apna_hisab.db"

    # CHANGE THIS in production (any long random string)
    jwt_secret: str = "dev-only-change-me-please-0f3c9a"
    jwt_algorithm: str = "HS256"
    jwt_expires_days: int = 30

    # Comma-separated list of frontend origins allowed to call the API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

    # "Today" for dashboard totals is computed in this timezone
    timezone: str = "Asia/Karachi"

    # Create the demo account (ayesha@example.pk / demo1234) with sample data on startup
    seed_demo: bool = True

    @property
    def sqlalchemy_url(self) -> str:
        """Hosting providers (Render, Railway, Neon) give 'postgres://' or 'postgresql://' URLs;
        SQLAlchemy needs the driver name, so add it automatically."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
