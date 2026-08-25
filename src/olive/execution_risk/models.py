from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class ExecutionRiskPolicyRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "execution_risk_policies"
    __table_args__ = (
        UniqueConstraint("configuration_version", name="uq_execution_risk_policy_version"),
    )

    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict[str, str | int]] = mapped_column(JSON, nullable=False)


class ExecutionRiskDecisionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "execution_risk_decisions"

    market_quote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_quotes.id", ondelete="RESTRICT"), nullable=False
    )
    execution_risk_policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_risk_policies.id", ondelete="RESTRICT"), nullable=False
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    approved_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    requested_notional: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    maximum_executable_notional: Mapped[Decimal] = mapped_column(
        Numeric(30, 12), nullable=False
    )
    slice_count: Mapped[int] = mapped_column(nullable=False)
    binding_limits: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
