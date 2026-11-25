"""Настройки приложения. Значения берутся из переменных окружения (см. .env.example)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://sputnik:sputnik_dev_password@localhost:5432/sputnik"
    )
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # токен живёт 24 часа (см. docs/openapi.yaml)
    media_dir: str = "./media"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    seed_on_start: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
