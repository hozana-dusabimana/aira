from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    APP_NAME: str = "AIRA"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    DATABASE_URL: str = "sqlite:///./aira.db"

    JWT_SECRET: str = "change-me-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    AI_ENABLED: bool = False
    AUTO_SEED: bool = True

    # Reject uploads the AI does not recognise as a reportable incident
    # (e.g. a person sitting in an office) so officers aren't disturbed by
    # non-incident photos. Set false to accept every upload.
    INCIDENT_VALIDATION_ENABLED: bool = True

    # --- Rate limiting -------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_USE_REDIS: bool = False
    RL_LOGIN: str = "10/minute"
    RL_REGISTER: str = "5/minute"
    RL_PASSWORD_RESET: str = "5/minute"
    RL_INCIDENT_SUBMIT: str = "20/minute"

    # --- Email (password reset codes, verification) -------------------
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM: str = "AIRA <no-reply@aira.local>"
    SMTP_TIMEOUT: int = 10

    # --- Push (FCM) ---------------------------------------------------
    FCM_SERVER_KEY: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
