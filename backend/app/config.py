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

    # --- Self-trained incident classifier ------------------------------
    # When enabled (and a trained checkpoint exists), our own CNN — trained by
    # backend/training/train_classifier.py — predicts the incident_type instead
    # of the rule-based guesser. Falls back to the rules if the model is missing
    # or torch is unavailable, so this is safe to leave on. CLASSIFIER_WEIGHTS
    # optionally overrides the default backend/weights/incident_classifier.pt.
    INCIDENT_CNN_ENABLED: bool = False
    CLASSIFIER_WEIGHTS: str = ""
    # Minimum CNN confidence required to trust its prediction over the rules.
    INCIDENT_CNN_MIN_CONFIDENCE: float = 0.45

    # Accident-biased acceptance: treat a photo as an ACCIDENT when the model's
    # accident probability is at least this, even if another class is top-1.
    # Calibrated so non-accident photos (which score ~0 for accident) are never
    # accepted, while borderline/distant accidents still get through.
    ACCIDENT_ACCEPT_THRESHOLD: float = 0.25

    # Reject uploads the AI does not recognise as a reportable incident
    # (e.g. a person sitting in an office) so officers aren't disturbed by
    # non-incident photos. Set false to accept every upload.
    INCIDENT_VALIDATION_ENABLED: bool = True

    # Allow-list of incident_type values that count as a reportable incident.
    # Everything else (including the model's `fire`/`general`) is rejected. The
    # app is scoped to ROAD ACCIDENTS, so by default only `traffic` is accepted.
    # Comma-separated; e.g. set to "traffic,fire" to also accept fire reports.
    ACCEPTED_INCIDENT_TYPES: str = "traffic"

    # --- Duplicate detection ------------------------------------------
    # When several people photograph the SAME accident, only the first report
    # becomes an active incident. A later report of the same incident_type
    # within DUPLICATE_RADIUS_METERS and DUPLICATE_WINDOW_MINUTES of an existing
    # one is treated as a duplicate: it is quarantined to the Spam page
    # (reason="duplicate") and linked to the original, so officers see a single
    # incident instead of many. Set DUPLICATE_DETECTION_ENABLED=false to keep
    # every report as its own incident.
    DUPLICATE_DETECTION_ENABLED: bool = True
    DUPLICATE_RADIUS_METERS: float = 150.0
    DUPLICATE_WINDOW_MINUTES: int = 180

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

    @property
    def accepted_incident_types_set(self) -> set[str]:
        return {t.strip().lower() for t in self.ACCEPTED_INCIDENT_TYPES.split(",") if t.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
