from __future__ import annotations

import uuid
from decimal import Decimal

from olive.paper.oms import PaperOms
from olive.paper.schemas import OrderStatus, PaperOrder, PaperOrderRequest, VenueSnapshot


class SandboxRateLimitError(RuntimeError):
    pass


class FirstVenueSandboxConnector:
    """Single deterministic venue adapter used for paper and sandbox acceptance."""

    def __init__(self, oms: PaperOms, *, balance: Decimal = Decimal("100000")) -> None:
        self.oms = oms
        self.balance = balance
        self.available = True
        self.rate_limited = False

    def balances(self) -> Decimal:
        self._check()
        return self.balance

    def place_order(self, request: PaperOrderRequest) -> PaperOrder:
        self._check()
        return self.oms.submit(request)

    def cancel_order(self, order_id: uuid.UUID) -> PaperOrder:
        self._check()
        return self.oms.cancel(order_id)

    def read_order(self, order_id: uuid.UUID) -> PaperOrder:
        self._check()
        return self.oms.orders[order_id]

    def positions(self) -> dict[uuid.UUID, Decimal]:
        self._check()
        return {key: value.quantity for key, value in self.oms.positions.items()}

    def snapshot(self) -> VenueSnapshot:
        self._check()
        open_orders = {
            order_id: order.request.quantity - order.filled_quantity
            for order_id, order in self.oms.orders.items()
            if order.status in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}
        }
        return VenueSnapshot(
            open_orders=open_orders,
            positions=self.positions(),
            balance=self.balance,
        )

    def _check(self) -> None:
        if not self.available:
            raise ConnectionError("sandbox venue is unavailable")
        if self.rate_limited:
            raise SandboxRateLimitError("sandbox venue rate limit exceeded")
