from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PAPER = "paper"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OLIVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_name: str = "Olive Trading Platform"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://olive:olive@localhost:5432/olive"
    redis_url: str = "redis://localhost:6379/0"
    dependency_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    signal_hmac_key_id: str = Field(default="tradingview-development", min_length=1)
    signal_hmac_secret: SecretStr | None = None
    signal_max_age_seconds: int = Field(default=300, gt=0, le=3600)
    signal_nonce_ttl_seconds: int = Field(default=900, gt=0, le=86400)
    signal_rate_limit: int = Field(default=60, gt=0, le=10000)
    signal_rate_window_seconds: int = Field(default=60, gt=0, le=3600)
    signal_max_payload_bytes: int = Field(default=65536, ge=1024, le=1048576)
    market_data_max_age_seconds: int = Field(default=10, gt=0, le=3600)
    market_data_max_future_skew_seconds: int = Field(default=2, ge=0, le=60)
    market_data_max_spread_pct: Decimal = Field(default=Decimal("5"), gt=0, le=100)
    market_data_max_price_jump_pct: Decimal = Field(default=Decimal("20"), gt=0, le=1000)
    paper_auto_execute: bool = False
    paper_equity: Decimal = Field(default=Decimal("100000"), gt=0)
    paper_available_margin: Decimal = Field(default=Decimal("50000"), ge=0)
    paper_requested_risk_pct: Decimal = Field(default=Decimal("1"), gt=0, le=100)
    paper_fee_rate: Decimal = Field(default=Decimal("0.001"), ge=0, le=1)

    @model_validator(mode="after")
    def validate_gateway_windows(self) -> Settings:
        if self.signal_nonce_ttl_seconds < self.signal_max_age_seconds:
            raise ValueError("signal nonce TTL must cover the full accepted signal age")
        if self.paper_auto_execute and self.app_env not in {
            AppEnvironment.PAPER,
            AppEnvironment.STAGING,
        }:
            raise ValueError("automatic paper execution is allowed only in paper or staging")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnvironment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()
