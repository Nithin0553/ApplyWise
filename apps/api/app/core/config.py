from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "replace-me-locally-with-a-random-32-byte-secret"
MIN_SECRET_KEY_BYTES = 32


class Settings(BaseSettings):
    app_env: str = "development"
    # Used as the F01 JWT signing key, so it must be a real secret outside
    # local development: at least 32 bytes, generated per environment, and
    # never committed. See .env.example.
    app_secret_key: str = DEFAULT_SECRET_KEY
    database_url: str = "postgresql+psycopg://applywise:applywise_dev@localhost:5432/applywise"
    ai_provider: str = "stub"
    ai_api_key: str | None = None

    # F01: authentication / RBAC
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # F01: origins allowed to call the API cross-origin (the Vite dev
    # server runs on a different port than uvicorn). Override per
    # environment via CORS_ORIGINS (JSON array, e.g. '["https://app.example.com"]') in .env.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        """Fail fast instead of signing tokens with a known or weak key."""
        # Normalize once so docs and prototype-only routes use the same environment policy.
        self.app_env = self.app_env.strip().lower()
        if self.app_env == "production" and (
            self.app_secret_key == DEFAULT_SECRET_KEY
            or len(self.app_secret_key.encode()) < MIN_SECRET_KEY_BYTES
        ):
            raise ValueError(
                "APP_SECRET_KEY must be set to a unique secret of at least "
                f"{MIN_SECRET_KEY_BYTES} bytes when APP_ENV=production."
            )
        return self


settings = Settings()
