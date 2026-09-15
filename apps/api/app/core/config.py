from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "replace-me-locally"
    database_url: str = "postgresql+psycopg://applywise:applywise_dev@localhost:5432/applywise"
    ai_provider: str = "stub"
    ai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
