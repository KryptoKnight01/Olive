from __future__ import annotations

import uuid
from decimal import Decimal

from olive.paper.oms import PaperOms
from olive.paper.protection import PositionProtectionEngine
from olive.paper.reconciliation import ReconciliationEngine
from olive.paper.sandbox import FirstVenueSandboxConnector
from olive.paper.schemas import (
    OrderSide,
    OrderType,
    PaperOrderRequest,
    PipelineResult,
    ProtectionStatus,
)


class PaperPipeline:
    def __init__(self, oms: PaperOms, venue: FirstVenueSandboxConnector) -> None:
        self.oms = oms
        self.venue = venue

    def execute_round_trip(
        self,
        *,
        signal_id: uuid.UUID,
        instrument_id: uuid.UUID,
        quantity: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
    ) -> PipelineResult:
        entry = self.venue.place_order(
            PaperOrderRequest(
                client_order_id=uuid.uuid4(),
                signal_id=signal_id,
                instrument_id=instrument_id,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=quantity,
            )
        )
        entry = self.oms.fill(entry.order_id, quantity, entry_price)
        protection = PositionProtectionEngine().assess(
            uuid.uuid4(),
            quantity,
            stop_quantities=[quantity],
            target_quantities=[quantity],
        )
        if protection.status is not ProtectionStatus.PROTECTED:
            raise RuntimeError("paper position protection failed")
        reconciliation = ReconciliationEngine().compare(
            internal_orders={},
            internal_positions={instrument_id: quantity},
            internal_balance=self.venue.balance,
            venue=self.venue.snapshot(),
        )
        if not reconciliation.matched:
            raise RuntimeError("paper venue reconciliation failed")
        exit_order = self.venue.place_order(
            PaperOrderRequest(
                client_order_id=uuid.uuid4(),
                signal_id=signal_id,
                instrument_id=instrument_id,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=quantity,
                reduce_only=True,
            )
        )
        exit_order = self.oms.fill(exit_order.order_id, quantity, exit_price)
        position = self.oms.positions[instrument_id]
        return PipelineResult(
            signal_id=signal_id,
            order_id=entry.order_id,
            order_status=exit_order.status,
            filled_quantity=entry.filled_quantity,
            protection_status=protection.status,
            reconciled=reconciliation.matched,
            realized_pnl=position.realized_pnl - position.fees,
        )
