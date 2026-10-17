"""Configuration management for Samanvay using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/samanvay"
    jwt_secret: str = ""

    # Embeddings
    embedding_provider: str = "local"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384

    # OCR
    ocr_provider: str = "fake"
    ocr_conf_min: float = 0.70
    ocr_fallback_conf: float = 0.80

    # LLM Extractor
    llm_extractor: str = "off"
    llm_base_url: str = "http://localhost:11434"

    # Matching & Tiering Thresholds
    tau_auto: float = 0.995
    tau_review: float = 0.750

    # Runtime Modes
    clock_mode: str = "real"
    demo_mode: bool = False
    demo_org_id: str = "OIL-1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    erp_target: str = "sap"
    storage_path: str = "./data/storage"
    upload_max_mb: int = Field(default=15, ge=1, le=100)

    # ML & Observability
    ml_layer: str = "off"
    metrics_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_runtime_security(self) -> None:
        if (
            not self.jwt_secret
            or len(self.jwt_secret) < 32
            or self.jwt_secret.startswith("replace-this-")
            or self.jwt_secret == "samanvay-super-secret-development-jwt-key-2026"
        ):
            raise ValueError("JWT_SECRET must be configured with at least 32 characters.")


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
