from __future__ import annotations

import uuid
from decimal import Decimal

from olive.paper.schemas import ReconciliationResult, VenueSnapshot


class ReconciliationEngine:
    def compare(
        self,
        *,
        internal_orders: dict[uuid.UUID, Decimal],
        internal_positions: dict[uuid.UUID, Decimal],
        internal_balance: Decimal,
        venue: VenueSnapshot,
    ) -> ReconciliationResult:
        mismatches: list[str] = []
        for order_id in sorted(set(internal_orders) | set(venue.open_orders), key=str):
            if internal_orders.get(order_id) != venue.open_orders.get(order_id):
                mismatches.append(f"order mismatch: {order_id}")
        for instrument_id in sorted(set(internal_positions) | set(venue.positions), key=str):
            if internal_positions.get(instrument_id, Decimal("0")) != venue.positions.get(
                instrument_id, Decimal("0")
            ):
                mismatches.append(f"position mismatch: {instrument_id}")
        if internal_balance != venue.balance:
            mismatches.append("balance mismatch")
        return ReconciliationResult(
            matched=not mismatches,
            suspend_entries=bool(mismatches),
            mismatches=mismatches,
        )
