import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # Core App Settings
    APP_NAME: str = "Sentinel AI Platform"
    APP_ENV: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="super-secret-production-key-change-in-env-32bytes", min_length=16)

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    WORKERS_COUNT: int = 4

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://app.sentinelai.io"
    ]

    # Supabase PostgreSQL Cloud Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sentinelai_db",
        description="Supabase PostgreSQL Cloud connection string (postgresql+asyncpg://...)"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # Recycles connections every 30 minutes for Supabase/PgBouncer
    DB_ECHO: bool = False

    @staticmethod
    def _sanitize_db_url(raw_url: str) -> str:
        raw_url = raw_url.strip()
        if "://" not in raw_url:
            return raw_url

        scheme, rest = raw_url.split("://", 1)
        if "@" in rest:
            last_at_idx = rest.rfind("@")
            user_pass = rest[:last_at_idx]
            host_part = rest[last_at_idx + 1:]
            if ":" in user_pass:
                user, password = user_pass.split(":", 1)
                password_encoded = password.replace("@", "%40")
                rest = f"{user}:{password_encoded}@{host_part}"
        return f"{scheme}://{rest}"

    @property
    def async_database_url(self) -> str:
        url = self._sanitize_db_url(self.DATABASE_URL)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        url = self._sanitize_db_url(self.DATABASE_URL)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    # Vector Database Settings (ChromaDB)
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000
    CHROMADB_PATH: str = "./data/chromadb"
    CHROMADB_PERSIST_DIRECTORY: str = "./data/chromadb"
    CHROMADB_COLLECTION_PREFIX: str = "sentinelai"
    CHROMADB_IS_REMOTE: bool = False

    # Cache Settings (Redis)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 20
    DEFAULT_CACHE_TTL: int = 300  # 5 minutes

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # AI & LLM Settings
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_TOKENS: int = 4096

    # ── Google Cloud Platform Settings ──────────────────────────────────
    GCP_PROJECT_ID: str = Field(default="", description="Google Cloud project ID")
    GCP_LOCATION: str = Field(default="us-central1", description="Google Cloud region")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = Field(
        default=None, description="Path to GCP service-account JSON key file"
    )

    # BigQuery (telemetry warehouse + BigQuery ML anomaly detection)
    BIGQUERY_ENABLED: bool = Field(default=True, description="BigQuery telemetry warehouse (primary)")
    BIGQUERY_DATASET: str = Field(default="sentinelai", description="BigQuery dataset name")
    BIGQUERY_TELEMETRY_TABLE: str = Field(default="telemetry_events", description="BigQuery telemetry table")
    BIGQUERY_ANOMALY_MODEL: str = Field(default="error_rate_arima", description="BigQuery ML ARIMA+ model name")

    # Pub/Sub (primary async event bus)
    PUBSUB_ENABLED: bool = Field(default=True, description="Google Pub/Sub event bus (primary)")
    PUBSUB_TELEMETRY_TOPIC: str = Field(default="telemetry-events", description="Pub/Sub telemetry topic")
    PUBSUB_INCIDENT_TOPIC: str = Field(default="incident-events", description="Pub/Sub incident topic")
    PUBSUB_RCA_TOPIC: str = Field(default="ai-rca-events", description="Pub/Sub RCA topic")

    # Firestore (live incident-state store)
    FIRESTORE_ENABLED: bool = Field(default=True, description="Firestore live incident state (primary)")
    FIRESTORE_INCIDENTS_COLLECTION: str = Field(
        default="incidents_live", description="Firestore collection for live incident state"
    )

    # Vertex AI (managed embeddings — primary)
    VERTEX_AI_ENABLED: bool = Field(default=True, description="Vertex AI managed embeddings (primary)")
    VERTEX_EMBEDDING_MODEL: str = Field(
        default="text-embedding-004", description="Vertex AI embedding model name"
    )

    # RAG Settings
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.65
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # Ingestion & SDK Settings
    INGESTION_MAX_BATCH_SIZE: int = 500
    INGESTION_MAX_PAYLOAD_MB: int = 10
    RATE_LIMIT_SDK_PER_MINUTE: int = 10000
    RATE_LIMIT_API_PER_MINUTE: int = 300

    # Auth & JWT Settings
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Notification & SMTP Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "alerts@sentinelai.io"
    EMAILS_FROM_NAME: str = "Sentinel AI Alerts"

    # Observability
    PROMETHEUS_ENABLED: bool = True


settings = Settings()
