from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class MobileControlRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "mobile_control_decisions"
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    permitted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)


class MlGuardrailRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "ml_guardrail_decisions"
    model_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    applied_multiplier: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class ProductionReleaseRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "production_release_decisions"
    release_version: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failed_checks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
