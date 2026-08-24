from __future__ import annotations

from decimal import Decimal

from olive.risk.schemas import (
    ExposureMetric,
    ExposurePosition,
    HierarchicalExposureLimit,
    HierarchicalRiskDecision,
    HierarchicalRiskInput,
    RiskDecisionOutcome,
)

ZERO = Decimal("0")
ONE = Decimal("1")


class HierarchicalExposureEngine:
    """Apply matching exposure limits and let the most restrictive limit win."""

    def evaluate(
        self,
        request: HierarchicalRiskInput,
        limits: tuple[HierarchicalExposureLimit, ...],
    ) -> HierarchicalRiskDecision:
        evaluations: list[dict[str, str]] = []
        fractions: list[tuple[str, Decimal]] = []
        for limit in limits:
            proposed_keys = request.proposed_tags.get(limit.dimension, ())
            if limit.scope_key not in proposed_keys:
                continue
            current = sum(
                (
                    self._position_value(position, limit.metric)
                    for position in request.positions
                    if limit.scope_key in position.tags.get(limit.dimension, ())
                ),
                ZERO,
            )
            proposed = self._proposed_value(request, limit.metric)
            remaining = limit.maximum - current
            fraction = ONE if proposed == ZERO else min(ONE, max(ZERO, remaining / proposed))
            label = f"{limit.dimension.value}:{limit.scope_key}:{limit.metric.value}"
            evaluations.append(
                {
                    "limit": label,
                    "current": str(current),
                    "proposed": str(proposed),
                    "maximum": str(limit.maximum),
                    "remaining": str(remaining),
                    "approved_fraction": str(fraction),
                }
            )
            fractions.append((label, fraction))

        if not fractions:
            return self._decision(request, ONE, None, evaluations, "no matching limits")
        binding_limit, fraction = min(fractions, key=lambda item: item[1])
        reason = (
            "all matching hierarchical limits satisfied"
            if fraction == ONE
            else f"most restrictive limit: {binding_limit}"
        )
        return self._decision(request, fraction, binding_limit, evaluations, reason)

    @staticmethod
    def _position_value(position: ExposurePosition, metric: ExposureMetric) -> Decimal:
        if metric is ExposureMetric.GROSS_NOTIONAL:
            return position.gross_notional
        if metric is ExposureMetric.OPEN_STOP_RISK:
            return position.open_stop_risk
        if metric is ExposureMetric.MARGIN_USED:
            return position.margin_used
        return ONE

    @staticmethod
    def _proposed_value(request: HierarchicalRiskInput, metric: ExposureMetric) -> Decimal:
        if metric is ExposureMetric.GROSS_NOTIONAL:
            return request.proposed_notional
        if metric is ExposureMetric.OPEN_STOP_RISK:
            return request.proposed_stop_risk
        if metric is ExposureMetric.MARGIN_USED:
            return request.proposed_margin
        return ONE

    @staticmethod
    def _decision(
        request: HierarchicalRiskInput,
        fraction: Decimal,
        binding_limit: str | None,
        evaluations: list[dict[str, str]],
        reason: str,
    ) -> HierarchicalRiskDecision:
        outcome = (
            RiskDecisionOutcome.REJECTED
            if fraction == ZERO
            else RiskDecisionOutcome.APPROVED
            if fraction == ONE
            else RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
        )
        return HierarchicalRiskDecision(
            decision=outcome,
            signal_id=request.signal_id,
            approved_fraction=fraction,
            approved_notional=request.proposed_notional * fraction,
            binding_limit=binding_limit,
            evaluations=evaluations,
            reasons=[reason],
        )
