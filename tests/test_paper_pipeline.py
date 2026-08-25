from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from olive.paper.oms import PaperOms, PaperOmsError
from olive.paper.pipeline import PaperPipeline
from olive.paper.protection import PositionProtectionEngine
from olive.paper.reconciliation import ReconciliationEngine
from olive.paper.sandbox import FirstVenueSandboxConnector, SandboxRateLimitError
from olive.paper.schemas import (
    OrderSide,
    OrderStatus,
    OrderType,
    PaperOrderRequest,
    ProtectionStatus,
    VenueSnapshot,
)


def order(instrument_id: uuid.UUID, **changes: object) -> PaperOrderRequest:
    values: dict[str, object] = {
        "client_order_id": uuid.uuid4(),
        "signal_id": uuid.uuid4(),
        "instrument_id": instrument_id,
        "side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "quantity": Decimal("10"),
    }
    values.update(changes)
    return PaperOrderRequest.model_validate(values)


def test_oms_supports_partial_and_complete_fills() -> None:
    oms = PaperOms()
    submitted = oms.submit(order(uuid.uuid4()))
    partial = oms.fill(submitted.order_id, Decimal("4"), Decimal("100"))
    complete = oms.fill(submitted.order_id, Decimal("6"), Decimal("101"))
    assert partial.status is OrderStatus.PARTIALLY_FILLED
    assert complete.status is OrderStatus.FILLED
    assert complete.average_fill_price == Decimal("100.6")


def test_order_submission_is_idempotent() -> None:
    oms = PaperOms()
    request = order(uuid.uuid4())
    assert oms.submit(request).order_id == oms.submit(request).order_id


def test_reduce_only_cannot_increase_position() -> None:
    oms = PaperOms()
    with pytest.raises(PaperOmsError, match="reduce-only"):
        oms.submit(order(uuid.uuid4(), side=OrderSide.SELL, reduce_only=True))


def test_protection_detects_missing_target() -> None:
    result = PositionProtectionEngine().assess(
        uuid.uuid4(), Decimal("10"), stop_quantities=[Decimal("10")], target_quantities=[]
    )
    assert result.status is ProtectionStatus.UNPROTECTED
    assert result.critical


def test_protection_detects_quantity_mismatch() -> None:
    result = PositionProtectionEngine().assess(
        uuid.uuid4(),
        Decimal("10"),
        stop_quantities=[Decimal("8")],
        target_quantities=[Decimal("10")],
    )
    assert result.status is ProtectionStatus.QUANTITY_MISMATCH


def test_reconciliation_suspends_entries_on_position_mismatch() -> None:
    instrument_id = uuid.uuid4()
    result = ReconciliationEngine().compare(
        internal_orders={},
        internal_positions={instrument_id: Decimal("10")},
        internal_balance=Decimal("1000"),
        venue=VenueSnapshot(
            open_orders={}, positions={instrument_id: Decimal("9")}, balance=Decimal("1000")
        ),
    )
    assert not result.matched
    assert result.suspend_entries


def test_sandbox_exposes_rate_limit_failure() -> None:
    venue = FirstVenueSandboxConnector(PaperOms())
    venue.rate_limited = True
    with pytest.raises(SandboxRateLimitError):
        venue.balances()


def test_end_to_end_paper_round_trip() -> None:
    oms = PaperOms(fee_rate=Decimal("0.001"))
    venue = FirstVenueSandboxConnector(oms)
    result = PaperPipeline(oms, venue).execute_round_trip(
        signal_id=uuid.uuid4(),
        instrument_id=uuid.uuid4(),
        quantity=Decimal("2"),
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
    )
    assert result.order_status is OrderStatus.FILLED
    assert result.protection_status is ProtectionStatus.PROTECTED
    assert result.reconciled
    assert result.realized_pnl == Decimal("19.58")
