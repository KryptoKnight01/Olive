from __future__ import annotations

import uuid
from decimal import Decimal

from olive.paper.schemas import (
    OrderSide,
    OrderStatus,
    PaperFill,
    PaperOrder,
    PaperOrderRequest,
    PaperPosition,
)


class PaperOmsError(ValueError):
    pass


class PaperOms:
    def __init__(self, *, fee_rate: Decimal = Decimal("0.001")) -> None:
        self.fee_rate = fee_rate
        self.orders: dict[uuid.UUID, PaperOrder] = {}
        self.client_orders: dict[uuid.UUID, uuid.UUID] = {}
        self.positions: dict[uuid.UUID, PaperPosition] = {}

    def submit(self, request: PaperOrderRequest) -> PaperOrder:
        existing_id = self.client_orders.get(request.client_order_id)
        if existing_id is not None:
            return self.orders[existing_id]
        if request.reduce_only:
            position = self.positions.get(request.instrument_id)
            signed = request.quantity if request.side is OrderSide.BUY else -request.quantity
            if (
                position is None
                or abs(signed) > abs(position.quantity)
                or signed * position.quantity > 0
            ):
                raise PaperOmsError("reduce-only order would increase or reverse the position")
        order = PaperOrder(
            order_id=uuid.uuid4(),
            request=request,
            status=OrderStatus.NEW,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            fees=Decimal("0"),
            fills=[],
        )
        self.orders[order.order_id] = order
        self.client_orders[request.client_order_id] = order.order_id
        return order

    def fill(self, order_id: uuid.UUID, quantity: Decimal, price: Decimal) -> PaperOrder:
        order = self.orders[order_id]
        if order.status not in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
            raise PaperOmsError("order cannot receive fills in its current state")
        remaining = order.request.quantity - order.filled_quantity
        if quantity <= 0 or quantity > remaining:
            raise PaperOmsError("fill quantity exceeds the open order quantity")
        fee = quantity * price * self.fee_rate
        total_cost = (order.average_fill_price or Decimal("0")) * order.filled_quantity
        average = (total_cost + price * quantity) / (order.filled_quantity + quantity)
        fill = PaperFill(
            fill_id=uuid.uuid4(), order_id=order_id, quantity=quantity, price=price, fee=fee
        )
        filled = order.filled_quantity + quantity
        updated = order.model_copy(
            update={
                "status": (
                    OrderStatus.FILLED
                    if filled == order.request.quantity
                    else OrderStatus.PARTIALLY_FILLED
                ),
                "filled_quantity": filled,
                "average_fill_price": average,
                "fees": order.fees + fee,
                "fills": [*order.fills, fill],
            }
        )
        self.orders[order_id] = updated
        self._apply_position(updated.request, quantity, price, fee)
        return updated

    def cancel(self, order_id: uuid.UUID) -> PaperOrder:
        order = self.orders[order_id]
        if order.status not in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
            raise PaperOmsError("only open orders may be cancelled")
        updated = order.model_copy(update={"status": OrderStatus.CANCELLED})
        self.orders[order_id] = updated
        return updated

    def _apply_position(
        self, request: PaperOrderRequest, quantity: Decimal, price: Decimal, fee: Decimal
    ) -> None:
        signed = quantity if request.side is OrderSide.BUY else -quantity
        current = self.positions.get(request.instrument_id)
        if current is None:
            self.positions[request.instrument_id] = PaperPosition(
                instrument_id=request.instrument_id,
                quantity=signed,
                average_entry_price=price,
                realized_pnl=Decimal("0"),
                fees=fee,
            )
            return
        same_direction = current.quantity * signed > 0
        if same_direction:
            total = abs(current.quantity) + abs(signed)
            average = (
                current.average_entry_price * abs(current.quantity) + price * abs(signed)
            ) / total
            realized = current.realized_pnl
        else:
            closed = min(abs(current.quantity), abs(signed))
            direction = Decimal("1") if current.quantity > 0 else Decimal("-1")
            realized = (
                current.realized_pnl + (price - current.average_entry_price) * closed * direction
            )
            average = current.average_entry_price if abs(signed) <= abs(current.quantity) else price
        self.positions[request.instrument_id] = PaperPosition(
            instrument_id=request.instrument_id,
            quantity=current.quantity + signed,
            average_entry_price=average,
            realized_pnl=realized,
            fees=current.fees + fee,
        )
