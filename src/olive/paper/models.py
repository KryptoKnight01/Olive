from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class PaperOrderRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "paper_orders"
    client_order_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    signal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    average_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    fees: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    reduce_only: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PaperFillRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "paper_fills"
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("paper_orders.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)


class PaperPositionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "paper_positions"
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    average_entry_price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)


class ProtectionAssessmentRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "protection_assessments"
    position_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    stop_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    critical: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class ReconciliationRunRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "reconciliation_runs"
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    suspend_entries: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mismatches: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class SandboxOperationRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "sandbox_operations"
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)


class PaperPipelineRunRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "paper_pipeline_runs"
    signal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    order_status: Mapped[str] = mapped_column(String(24), nullable=False)
    protection_status: Mapped[str] = mapped_column(String(24), nullable=False)
    reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
