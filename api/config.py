"""Configuration management for Samanvay using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/samanvay"
    jwt_secret: str = "samanvay-super-secret-development-jwt-key-2026"

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
    demo_mode: bool = True
    erp_target: str = "sap"
    storage_path: str = "./data/storage"
    upload_max_mb: int = 15

    # ML & Observability
    ml_layer: str = "off"
    metrics_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
