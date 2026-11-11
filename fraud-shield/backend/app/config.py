"""Application Configuration Module.

Loads settings from environment variables and .env file with safe defaults.
"""
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class for Fraud Shield."""

    # Project metadata
    APP_NAME: str = "Fraud Shield"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security secrets
    SECRET_KEY: str = "fraud-shield-academic-secret-key-change-in-production"
    HMAC_SECRET_KEY: str = "fraud-shield-hmac-key-2026"

    # Database
    DATABASE_URL: str = "sqlite:///./fraud_shield.db"

    # Risk Engine Thresholds (Configurable)
    # Low Risk: < 0.45, Medium Risk: [0.45, 0.80), High Risk: >= 0.80
    RISK_THRESHOLD_LOW: float = 0.45
    RISK_THRESHOLD_HIGH: float = 0.80

    # OTP Lifecycle Settings
    OTP_EXPIRY_SECONDS: int = 180
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RESEND_MAX: int = 2

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

