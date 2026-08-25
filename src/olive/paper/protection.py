from __future__ import annotations

import uuid
from decimal import Decimal

from olive.paper.schemas import ProtectionAssessment, ProtectionStatus


class PositionProtectionEngine:
    def assess(
        self,
        position_id: uuid.UUID,
        position_quantity: Decimal,
        *,
        stop_quantities: list[Decimal],
        target_quantities: list[Decimal],
        orphan_order_count: int = 0,
    ) -> ProtectionAssessment:
        required = abs(position_quantity)
        stop_total = sum(stop_quantities, Decimal("0"))
        target_total = sum(target_quantities, Decimal("0"))
        if orphan_order_count:
            status = ProtectionStatus.ORPHAN_ORDERS
            reasons = ["reduce-only protection orders exist without a matching position"]
        elif required == 0:
            status = ProtectionStatus.PROTECTED
            reasons = ["flat position requires no protective orders"]
        elif stop_total == 0 or target_total == 0:
            status = ProtectionStatus.UNPROTECTED
            reasons = ["position is missing a protective stop or target"]
        elif stop_total != required or target_total > required:
            status = ProtectionStatus.QUANTITY_MISMATCH
            reasons = ["protective order quantities do not match the open position"]
        else:
            status = ProtectionStatus.PROTECTED
            reasons = ["stop and target protection covers the open position"]
        return ProtectionAssessment(
            position_id=position_id,
            status=status,
            stop_quantity=stop_total,
            target_quantity=target_total,
            critical=status is not ProtectionStatus.PROTECTED,
            reasons=reasons,
        )
