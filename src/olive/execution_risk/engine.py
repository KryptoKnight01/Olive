from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from olive.execution_risk.schemas import (
    ExecutionRiskAction,
    ExecutionRiskDecision,
    ExecutionRiskInput,
    ExecutionRiskPolicy,
)


class ExecutionRiskEngine:
    def evaluate(
        self, request: ExecutionRiskInput, policy: ExecutionRiskPolicy
    ) -> ExecutionRiskDecision:
        if request.market_data_status != "VALID":
            return self._decision(
                request, ExecutionRiskAction.REJECT, Decimal("0"), 0,
                ["market_data_status"], ["authoritative market data is not valid"],
            )
        if request.spread_pct > policy.maximum_spread_pct:
            return self._decision(
                request, ExecutionRiskAction.DEFER, Decimal("0"), 0,
                ["maximum_spread_pct"], ["spread exceeds the execution threshold"],
            )
        if request.expected_slippage_pct > policy.maximum_slippage_pct:
            return self._decision(
                request, ExecutionRiskAction.DEFER, Decimal("0"), 0,
                ["maximum_slippage_pct"], ["expected slippage exceeds the execution threshold"],
            )

        adv_capacity = (
            request.average_daily_volume_notional
            * policy.maximum_adv_participation_pct
            / Decimal("100")
        )
        book_capacity = (
            request.available_book_notional
            * policy.maximum_book_participation_pct
            / Decimal("100")
        )
        capacity = min(adv_capacity, book_capacity)
        bindings = [
            name
            for name, value in (
                ("maximum_adv_participation_pct", adv_capacity),
                ("maximum_book_participation_pct", book_capacity),
            )
            if value == capacity
        ]
        if capacity < policy.minimum_executable_notional:
            return self._decision(
                request, ExecutionRiskAction.REJECT, Decimal("0"), 0, bindings,
                ["liquidity capacity is below the minimum executable notional"],
            )
        if request.requested_notional <= capacity:
            return self._decision(
                request, ExecutionRiskAction.APPROVE, request.requested_notional, 1, [],
                ["order fits configured liquidity and participation limits"],
            )

        fraction = capacity / request.requested_notional
        if fraction >= policy.minimum_reduced_fraction:
            return self._decision(
                request, ExecutionRiskAction.REDUCE, capacity, 1, bindings,
                ["order reduced to the most restrictive liquidity capacity"],
            )
        slices = int(
            (request.requested_notional / capacity).to_integral_value(rounding=ROUND_DOWN)
        )
        if request.requested_notional % capacity:
            slices += 1
        if slices <= policy.maximum_slices:
            return self._decision(
                request, ExecutionRiskAction.SPLIT, request.requested_notional, slices, bindings,
                ["order must be split to remain within per-slice participation limits"],
            )
        return self._decision(
            request, ExecutionRiskAction.REJECT, Decimal("0"), 0, bindings,
            ["required slice count exceeds the configured maximum"],
        )

    @staticmethod
    def _decision(
        request: ExecutionRiskInput,
        action: ExecutionRiskAction,
        approved_notional: Decimal,
        slices: int,
        bindings: list[str],
        reasons: list[str],
    ) -> ExecutionRiskDecision:
        approved_quantity = (
            request.requested_quantity * approved_notional / request.requested_notional
        )
        return ExecutionRiskDecision(
            signal_id=request.signal_id,
            action=action,
            requested_quantity=request.requested_quantity,
            approved_quantity=approved_quantity,
            requested_notional=request.requested_notional,
            approved_notional=approved_notional,
            maximum_executable_notional=approved_notional,
            slice_count=slices,
            binding_limits=bindings,
            reasons=reasons,
        )
