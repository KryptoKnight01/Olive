from __future__ import annotations

from decimal import Decimal

from olive.risk.schemas import (
    CorrelationRiskDecision,
    CorrelationRiskInput,
    CorrelationRiskPolicy,
    RiskDecisionOutcome,
)

ZERO = Decimal("0")
ONE = Decimal("1")


class CorrelationRiskEngine:
    """Build deterministic return-correlation clusters and enforce their limits."""

    def evaluate(
        self, request: CorrelationRiskInput, policy: CorrelationRiskPolicy
    ) -> CorrelationRiskDecision:
        if policy.minimum_observations > policy.lookback_observations:
            return self._decision(request, ZERO, (), {}, 0, ZERO, "invalid correlation policy")
        histories = {
            key: values[-policy.lookback_observations :]
            for key, values in request.price_history.items()
            if len(values) >= policy.minimum_observations
        }
        if request.proposed_instrument_key not in histories:
            return self._decision(
                request, ZERO, (), {}, 0, ZERO, "proposed instrument has insufficient history"
            )
        correlations = self._correlations(histories)
        cluster = self._cluster(
            request.proposed_instrument_key, histories, correlations, policy.cluster_threshold
        )
        open_keys = {
            position.instrument_key
            for position in request.positions
            if position.open_stop_risk > ZERO
        }
        cluster_positions = len(open_keys.intersection(cluster))
        proposed_is_open = request.proposed_instrument_key in open_keys
        if not proposed_is_open and cluster_positions >= policy.max_correlated_positions:
            return self._decision(
                request,
                ZERO,
                cluster,
                correlations,
                cluster_positions,
                self._cluster_risk(request, cluster),
                "maximum correlated positions reached",
            )
        current_risk = self._cluster_risk(request, cluster)
        fraction = min(
            ONE,
            max(ZERO, (policy.max_cluster_stop_risk - current_risk) / request.proposed_stop_risk),
        )
        reason = (
            "correlation cluster limits satisfied"
            if fraction == ONE
            else "cluster stop-risk limit is binding"
        )
        return self._decision(
            request, fraction, cluster, correlations, cluster_positions, current_risk, reason
        )

    @staticmethod
    def _returns(prices: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
        return tuple(prices[index] / prices[index - 1] - ONE for index in range(1, len(prices)))

    def _correlations(
        self, histories: dict[str, tuple[Decimal, ...]]
    ) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        keys = sorted(histories)
        for left_index, left in enumerate(keys):
            for right in keys[left_index + 1 :]:
                left_returns = self._returns(histories[left])
                right_returns = self._returns(histories[right])
                count = min(len(left_returns), len(right_returns))
                correlation = self._pearson(left_returns[-count:], right_returns[-count:])
                result[f"{left}|{right}"] = correlation
        return result

    @staticmethod
    def _pearson(left: tuple[Decimal, ...], right: tuple[Decimal, ...]) -> Decimal:
        count = Decimal(len(left))
        left_mean = sum(left, ZERO) / count
        right_mean = sum(right, ZERO) / count
        covariance = sum(
            ((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True)),
            ZERO,
        )
        left_variance = sum(((value - left_mean) ** 2 for value in left), ZERO)
        right_variance = sum(((value - right_mean) ** 2 for value in right), ZERO)
        denominator = (left_variance * right_variance).sqrt()
        return ZERO if denominator == ZERO else covariance / denominator

    @staticmethod
    def _cluster(
        proposed: str,
        histories: dict[str, tuple[Decimal, ...]],
        correlations: dict[str, Decimal],
        threshold: Decimal,
    ) -> tuple[str, ...]:
        cluster = {proposed}
        changed = True
        while changed:
            changed = False
            for key in histories:
                if key in cluster:
                    continue
                if any(
                    abs(correlations.get("|".join(sorted((key, member))), ZERO)) >= threshold
                    for member in cluster
                ):
                    cluster.add(key)
                    changed = True
        return tuple(sorted(cluster))

    @staticmethod
    def _cluster_risk(request: CorrelationRiskInput, cluster: tuple[str, ...]) -> Decimal:
        return sum(
            (
                position.open_stop_risk
                for position in request.positions
                if position.instrument_key in cluster
            ),
            ZERO,
        )

    @staticmethod
    def _decision(
        request: CorrelationRiskInput,
        fraction: Decimal,
        cluster: tuple[str, ...],
        correlations: dict[str, Decimal],
        position_count: int,
        current_risk: Decimal,
        reason: str,
    ) -> CorrelationRiskDecision:
        outcome = (
            RiskDecisionOutcome.REJECTED
            if fraction == ZERO
            else RiskDecisionOutcome.APPROVED
            if fraction == ONE
            else RiskDecisionOutcome.APPROVED_WITH_REDUCED_SIZE
        )
        return CorrelationRiskDecision(
            decision=outcome,
            signal_id=request.signal_id,
            approved_fraction=fraction,
            approved_notional=request.proposed_notional * fraction,
            proposed_cluster=cluster,
            correlations=correlations,
            current_cluster_positions=position_count,
            current_cluster_stop_risk=current_risk,
            projected_cluster_stop_risk=current_risk + request.proposed_stop_risk * fraction,
            reasons=[reason],
        )
