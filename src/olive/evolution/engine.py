from __future__ import annotations

from decimal import Decimal

from olive.evolution.schemas import (
    AuthorityDecision,
    AuthorityPolicy,
    CapitalPool,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionSlice,
    ExecutionStyle,
    NativeSignal,
    ParityResult,
    PoolAllocation,
    PortfolioAnalytics,
    PortfolioAnalyticsInput,
    SignalAuthority,
    StrategyBar,
)


class EvolutionEngine:
    def allocate_pool(self, pool: CapitalPool, requested_notional: Decimal) -> PoolAllocation:
        available = max(Decimal("0"), pool.allocated_capital - pool.reserved_capital)
        approved = min(requested_notional, available)
        return PoolAllocation(
            pool_key=pool.pool_key,
            approved_notional=approved,
            available_capital=available,
            unit_value=pool.allocated_capital / pool.investor_units,
            reason="CAPITAL_POOL_APPROVED"
            if approved == requested_notional
            else "CAPITAL_POOL_CAPPED",
        )

    def build_execution_plan(
        self,
        request: ExecutionRequest,
        style: ExecutionStyle,
        volume_weights: tuple[Decimal, ...] | None = None,
    ) -> ExecutionPlan:
        if style is ExecutionStyle.VWAP:
            if volume_weights is None or len(volume_weights) != request.slices:
                raise ValueError("VWAP requires one volume weight per slice")
            total_weight = sum(volume_weights, start=Decimal("0"))
            if total_weight <= 0:
                raise ValueError("VWAP weights must sum to a positive value")
            quantities = [
                request.total_quantity * weight / total_weight for weight in volume_weights
            ]
        else:
            quantities = [request.total_quantity / request.slices] * request.slices
        slices = tuple(
            ExecutionSlice(
                sequence=index + 1,
                minute_offset=index * request.duration_minutes // request.slices,
                quantity=quantity.quantize(Decimal("0.00000001")),
                limit_price=(
                    request.reference_price * (Decimal("1") - Decimal(index) / Decimal("10000"))
                ).quantize(Decimal("0.00000001")),
            )
            for index, quantity in enumerate(quantities)
        )
        return ExecutionPlan(
            order_id=request.order_id,
            style=style,
            slices=slices,
            total_quantity=sum((item.quantity for item in slices), start=Decimal("0")),
        )

    def analyze_portfolio(self, data: PortfolioAnalyticsInput) -> PortfolioAnalytics:
        assets = sorted(data.position_values)
        lengths = {len(data.returns[a]) for a in assets}
        if not lengths or len(lengths) != 1 or next(iter(lengths)) < 2:
            raise ValueError("aligned return histories with at least two observations are required")
        covariance: dict[str, dict[str, Decimal]] = {}
        for left in assets:
            covariance[left] = {}
            for right in assets:
                xs, ys = data.returns[left], data.returns[right]
                mx = sum(xs, Decimal("0")) / len(xs)
                my = sum(ys, Decimal("0")) / len(ys)
                covariance[left][right] = sum(
                    ((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)), Decimal("0")
                ) / (len(xs) - 1)
        portfolio_returns = []
        count = next(iter(lengths))
        for index in range(count):
            portfolio_returns.append(
                sum(
                    (
                        data.position_values[a] / data.portfolio_value * data.returns[a][index]
                        for a in assets
                    ),
                    Decimal("0"),
                )
            )
        losses = sorted(
            (-value * data.portfolio_value for value in portfolio_returns), reverse=True
        )
        tail_count = max(1, (len(losses) * int(Decimal("100") - data.confidence_pct) + 99) // 100)
        tail = losses[:tail_count]
        var = tail[-1]
        es = sum(tail, Decimal("0")) / len(tail)
        absolute = sum((abs(v) for v in data.position_values.values()), Decimal("0"))
        contributions = {
            asset: (abs(data.position_values[asset]) / absolute if absolute else Decimal("0"))
            for asset in assets
        }
        return PortfolioAnalytics(
            value_at_risk=var,
            expected_shortfall=es,
            risk_contribution=contributions,
            covariance=covariance,
        )

    def native_signal(self, strategy_key: str, bar: StrategyBar, version: str) -> NativeSignal:
        if bar.close > bar.fast_average > bar.slow_average:
            return NativeSignal(
                strategy_key=strategy_key,
                direction=1,
                reason="PRICE_AND_FAST_ABOVE_SLOW",
                specification_version=version,
            )
        if bar.close < bar.fast_average < bar.slow_average:
            return NativeSignal(
                strategy_key=strategy_key,
                direction=-1,
                reason="PRICE_AND_FAST_BELOW_SLOW",
                specification_version=version,
            )
        return NativeSignal(
            strategy_key=strategy_key,
            direction=0,
            reason="NO_CONFIRMED_TREND",
            specification_version=version,
        )

    def check_parity(
        self, native: list[int], pine: list[int], minimum_pct: Decimal
    ) -> ParityResult:
        if not native or len(native) != len(pine):
            raise ValueError("aligned non-empty signal histories are required")
        matches = sum(1 for left, right in zip(native, pine, strict=True) if left == right)
        parity = (Decimal(matches) / Decimal(len(native)) * 100).quantize(Decimal("0.01"))
        return ParityResult(
            samples=len(native), matches=matches, parity_pct=parity, passed=parity >= minimum_pct
        )

    def decide_authority(self, policy: AuthorityPolicy) -> AuthorityDecision:
        reasons: list[str] = []
        granted = policy.authority is not SignalAuthority.NATIVE_PYTHON
        if policy.authority is SignalAuthority.NATIVE_PYTHON:
            if policy.observed_parity_pct < policy.minimum_parity_pct:
                reasons.append("PARITY_THRESHOLD_NOT_MET")
            if not policy.review_approved:
                reasons.append("AUTHORITY_REVIEW_NOT_APPROVED")
            granted = not reasons
        return AuthorityDecision(
            source=policy.authority,
            production_authority_granted=granted,
            tradingview_required=policy.authority is not SignalAuthority.NATIVE_PYTHON
            or not granted,
            reasons=tuple(reasons) if reasons else ("AUTHORITY_POLICY_APPROVED",),
        )
