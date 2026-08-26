from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MobileAction(StrEnum):
    VIEW = "VIEW"
    PAUSE_STRATEGY = "PAUSE_STRATEGY"
    EMERGENCY_HALT = "EMERGENCY_HALT"
    CHANGE_CONFIGURATION = "CHANGE_CONFIGURATION"


class MobileSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    health: str
    alerts: tuple[str, ...]
    open_positions: int = Field(ge=0)
    active_signals: int = Field(ge=0)
    gross_exposure: Decimal = Field(ge=0)
    risk_state: str
    strategies_paused: tuple[str, ...]


class MobileControlRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: str
    role: str
    mfa_verified: bool
    action: MobileAction
    strategy_key: str | None = None


class MobileControlDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    permitted: bool
    requires_web: bool
    reason: str


class MlRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)
    model_key: str
    model_version: str
    risk_multiplier: Decimal = Field(ge=0)
    confidence: Decimal = Field(ge=0, le=1)
    explanation: tuple[str, ...]


class GuardedMlDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    applied_multiplier: Decimal
    accepted: bool
    reasons: tuple[str, ...]


class AnomalyObservation(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str
    value: Decimal
    baseline_mean: Decimal
    baseline_stddev: Decimal = Field(gt=0)
    threshold_z: Decimal = Field(gt=0)


class AnomalyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str
    z_score: Decimal
    anomalous: bool


class HardeningCheck(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    passed: bool
    evidence: str
    mandatory: bool = True


class ProductionReleaseDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    approved: bool
    failed_checks: tuple[str, ...]
    checks: tuple[HardeningCheck, ...]
