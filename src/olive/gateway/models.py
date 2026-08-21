from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from olive.db import Base
from olive.domain.models import StrategyVersion, TimestampMixin, UuidMixin, VenueInstrument


class SignalIntakeStatus(StrEnum):
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"


class SignalDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PAPER = "paper"
    STAGING = "staging"
    PRODUCTION = "production"


def gateway_enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


class SignalIntakeRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "signal_intake_records"
    __table_args__ = (
        CheckConstraint("expected_rr IS NULL OR expected_rr >= 0", name="ck_signal_expected_rr"),
        CheckConstraint(
            "setup_score IS NULL OR (setup_score >= 0 AND setup_score <= 100)",
            name="ck_signal_setup_score",
        ),
        Index("ix_signal_intake_status_created", "status", "created_at"),
        Index("ix_signal_intake_payload_hash", "payload_hash"),
    )

    signal_id: Mapped[uuid.UUID | None] = mapped_column(unique=True)
    status: Mapped[SignalIntakeStatus] = mapped_column(
        gateway_enum(SignalIntakeStatus, "signal_intake_status"), nullable=False
    )
    rejection_code: Mapped[str | None] = mapped_column(String(64))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    strategy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="RESTRICT"), index=True
    )
    venue_instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("venue_instruments.id", ondelete="RESTRICT"), index=True
    )
    configuration_version: Mapped[str | None] = mapped_column(String(64))
    environment: Mapped[SignalEnvironment | None] = mapped_column(
        gateway_enum(SignalEnvironment, "signal_environment")
    )
    emitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    direction: Mapped[SignalDirection | None] = mapped_column(
        gateway_enum(SignalDirection, "signal_direction")
    )
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    reference_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    targets: Mapped[list[str] | None] = mapped_column(JSON)
    expected_rr: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    timeframe: Mapped[str | None] = mapped_column(String(32))
    setup_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    regime: Mapped[str | None] = mapped_column(String(64))

    strategy_version: Mapped[StrategyVersion | None] = relationship()
    venue_instrument: Mapped[VenueInstrument | None] = relationship()
