from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(StrEnum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PaperOrderRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    client_order_id: uuid.UUID
    signal_id: uuid.UUID
    instrument_id: uuid.UUID
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    reduce_only: bool = False


class PaperFill(BaseModel):
    model_config = ConfigDict(frozen=True)

    fill_id: uuid.UUID
    order_id: uuid.UUID
    quantity: Decimal
    price: Decimal
    fee: Decimal


class PaperOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: uuid.UUID
    request: PaperOrderRequest
    status: OrderStatus
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    fees: Decimal
    fills: list[PaperFill]


class PaperPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: uuid.UUID
    quantity: Decimal
    average_entry_price: Decimal
    realized_pnl: Decimal
    fees: Decimal


class ProtectionStatus(StrEnum):
    PROTECTED = "PROTECTED"
    UNPROTECTED = "UNPROTECTED"
    ORPHAN_ORDERS = "ORPHAN_ORDERS"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"


class ProtectionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    position_id: uuid.UUID
    status: ProtectionStatus
    stop_quantity: Decimal
    target_quantity: Decimal
    critical: bool
    reasons: list[str]


class VenueSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    open_orders: dict[uuid.UUID, Decimal]
    positions: dict[uuid.UUID, Decimal]
    balance: Decimal


class ReconciliationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    matched: bool
    suspend_entries: bool
    mismatches: list[str]


class PipelineResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    order_id: uuid.UUID
    order_status: OrderStatus
    filled_quantity: Decimal
    protection_status: ProtectionStatus
    reconciled: bool
    realized_pnl: Decimal
