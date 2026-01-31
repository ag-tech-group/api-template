from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/api_template"

    # Auth
    secret_key: str = "change-me-in-production"

    # Environment
    environment: str = "development"

    # CORS — comma-separated origins, e.g. "https://myapp.com,https://www.myapp.com"
    cors_origins: str = ""

    # Frontend URL (for OAuth redirect after callback, etc.)
    frontend_url: str = "http://localhost:5173"

    # Cookie auth
    cookie_domain: str | None = None

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def cookie_samesite(self) -> str:
        return "lax" if self.is_development else "none"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.is_development:
            return [f"http://localhost:{p}" for p in range(5100, 5200)]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_development:
            weak_secrets = {"change-me-in-production", "dev-secret-key-change-in-production", ""}
            if self.secret_key in weak_secrets or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be a strong random value in production (min 32 chars)"
                )
            if "postgres:postgres@" in self.database_url:
                raise ValueError("Default database credentials must not be used in production")
        return self


settings = Settings()
