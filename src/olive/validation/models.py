from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class SignalValidationPolicy(UuidMixin, TimestampMixin, Base):
    __tablename__ = "signal_validation_policies"
    __table_args__ = (
        UniqueConstraint("strategy_version_id", name="uq_signal_validation_policy_version"),
        CheckConstraint(
            "max_entry_deviation_pct >= 0", name="ck_validation_entry_deviation_nonnegative"
        ),
        CheckConstraint("min_expected_rr >= 0", name="ck_validation_min_rr_nonnegative"),
        CheckConstraint(
            "min_setup_score >= 0 AND min_setup_score <= 100",
            name="ck_validation_setup_score_range",
        ),
    )

    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_directions: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["LONG", "SHORT"], nullable=False
    )
    allowed_timeframes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    max_entry_deviation_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), default=Decimal("1.0"), nullable=False
    )
    min_expected_rr: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("1.5"), nullable=False
    )
    min_setup_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("0"), nullable=False
    )
    session_timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    session_start: Mapped[str | None] = mapped_column(String(5))
    session_end: Mapped[str | None] = mapped_column(String(5))
    allowed_weekdays: Mapped[list[int]] = mapped_column(
        JSON, default=lambda: list(range(7)), nullable=False
    )
