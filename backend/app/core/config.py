import json
from typing import Literal

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    APP_NAME: str = "Obelytics"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "obelytics"
    POSTGRES_USER: str = "obelytics"
    POSTGRES_PASSWORD: str = "obelytics_dev"
    DATABASE_URL_OVERRIDE: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 3
    DB_POOL_RECYCLE: int = 1800

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            url = self.DATABASE_URL_OVERRIDE
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def DATABASE_URL_SYNC(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            url = self.DATABASE_URL_OVERRIDE
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            return url
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_dev"
    REDIS_DB: int = 0
    REDIS_URL_OVERRIDE: str = ""

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_OVERRIDE:
            return self.REDIS_URL_OVERRIDE
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Cloudinary (file storage)
    CLOUDINARY_CLOUD_NAME: str = "h1gsnk4q"
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_UPLOAD_PRESET: str = "obelytics"
    CLOUDINARY_FOLDER_REPORTS: str = "reports"
    CLOUDINARY_FOLDER_LOGOS: str = "logos"
    CLOUDINARY_FOLDER_ACCREDITATION: str = "accreditation"

    # CORS — comma-separated origins
    # e.g. ALLOWED_ORIGINS=https://obelytics.bitstreamhq.com,http://localhost:3000
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @computed_field
    @property
    def ALLOWED_ORIGINS_LIST(self) -> list[str]:
        raw = self.ALLOWED_ORIGINS.strip()
        if raw.startswith("["):
            try:
                values = json.loads(raw)
                if isinstance(values, list):
                    return [str(o).strip() for o in values if str(o).strip()]
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Obelytics <noreply@yourdomain.com>"

    # Copilot
    COPILOT_MAX_OUTPUT_TOKENS: int = 2048

    # ── AI gateway (app/modules/ai) — every model call goes through it ────────
    # "local"  = an Ollama server you run (self-hosted: data stays on your servers)
    # "hosted" = any OpenAI-compatible Chat Completions API (DeepSeek, OpenAI, vLLM…)
    # Each organization can choose per feature; these are the defaults until it does.
    AI_INTEGRITY_PROVIDER: Literal["local", "hosted", "off"] = "local"
    AI_COPILOT_PROVIDER: Literal["local", "hosted", "off"] = "hosted"
    AI_TIMEOUT_SECONDS: float = 300.0

    AI_LOCAL_BASE_URL: str = "http://localhost:11434"
    AI_LOCAL_TEXT_MODEL: str = "qwen3.5:4b"
    AI_LOCAL_VISION_MODEL: str = "qwen3.5:4b"
    AI_LOCAL_CHAT_MODEL: str = "qwen3.5:4b"
    AI_LOCAL_CONTEXT_TOKENS: int = 16384
    AI_LOCAL_CONCURRENCY: int = 1

    AI_HOSTED_BASE_URL: str = ""
    AI_HOSTED_API_KEY: str = ""
    AI_HOSTED_TEXT_MODEL: str = ""
    AI_HOSTED_VISION_MODEL: str = ""  # empty: the hosted provider is not used to read photos
    AI_HOSTED_CHAT_MODEL: str = ""
    # json_schema: strict structured output (OpenAI, vLLM). json_object: JSON mode only (DeepSeek).
    AI_HOSTED_JSON_MODE: Literal["json_schema", "json_object"] = "json_schema"
    AI_HOSTED_EXTRA_BODY: dict = {}  # merged into every request body
    # true when the "hosted" server is your institution's own (then nothing is redacted)
    AI_HOSTED_SELF_HOSTED: bool = False
    AI_HOSTED_CONCURRENCY: int = 4
    AI_HOSTED_INPUT_USD_PER_MTOK: float = 0.0
    AI_HOSTED_OUTPUT_USD_PER_MTOK: float = 0.0
    # Optional separate endpoint for reading photos, e.g. text on DeepSeek (no vision)
    # and photos on another provider. Empty values fall back to the AI_HOSTED_* above.
    AI_HOSTED_VISION_BASE_URL: str = ""
    AI_HOSTED_VISION_API_KEY: str = ""
    AI_HOSTED_VISION_JSON_MODE: Literal["", "json_schema", "json_object"] = ""
    AI_HOSTED_VISION_EXTRA_BODY: dict = {}  # used only with a separate vision endpoint
    AI_HOSTED_VISION_INPUT_USD_PER_MTOK: float | None = None
    AI_HOSTED_VISION_OUTPUT_USD_PER_MTOK: float | None = None

    # Extra regex for institution-specific ID formats, redacted before external calls
    AI_REDACT_EXTRA_PATTERN: str = ""

    # Deprecated — used for the hosted provider when AI_HOSTED_API_KEY is not set
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    @field_validator(
        "AI_HOSTED_VISION_INPUT_USD_PER_MTOK", "AI_HOSTED_VISION_OUTPUT_USD_PER_MTOK", mode="before"
    )
    @classmethod
    def _blank_price_is_unset(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _hosted_provider_from_deepseek(self) -> "Settings":
        if self.AI_HOSTED_API_KEY or not self.DEEPSEEK_API_KEY:
            return self
        self.AI_HOSTED_API_KEY = self.DEEPSEEK_API_KEY
        self.AI_HOSTED_BASE_URL = self.AI_HOSTED_BASE_URL or self.DEEPSEEK_BASE_URL
        self.AI_HOSTED_CHAT_MODEL = self.AI_HOSTED_CHAT_MODEL or self.DEEPSEEK_MODEL
        self.AI_HOSTED_TEXT_MODEL = self.AI_HOSTED_TEXT_MODEL or self.DEEPSEEK_MODEL
        if "AI_HOSTED_JSON_MODE" not in self.model_fields_set:
            self.AI_HOSTED_JSON_MODE = "json_object"
        if not self.AI_HOSTED_EXTRA_BODY:
            self.AI_HOSTED_EXTRA_BODY = {"thinking": {"type": "disabled"}}
        return self

    # ── Assessment integrity auditor ──────────────────────────────────────────
    INTEGRITY_MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
    INTEGRITY_MAX_PAGES: int = 8
    # Independent judgments per question; confidence = how often they agree (self-consistency)
    INTEGRITY_AUDIT_SAMPLES: int = 3
    INTEGRITY_MIN_CONFIDENCE: float = 0.5
    # Optional JSON file mapping raw confidence to measured accuracy (fitted on the gold set)
    INTEGRITY_CALIBRATION_FILE: str = ""
    # "arq": the background worker reads papers and runs audits (production).
    # "inline": run them in the API process — for local development without a worker.
    INTEGRITY_JOB_RUNNER: Literal["arq", "inline"] = "inline"
    INTEGRITY_JOB_TIMEOUT_SECONDS: int = 1800


settings = Settings()
