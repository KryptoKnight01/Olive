from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from olive.market_data.schemas import (
    MarketDataPolicy,
    MarketDataStatus,
    QuoteAssessment,
    QuoteInput,
)


class MarketDataQualityEngine:
    def assess_quote(
        self,
        quote: QuoteInput,
        policy: MarketDataPolicy,
        *,
        evaluated_at: datetime,
        previous_mid: Decimal | None = None,
    ) -> QuoteAssessment:
        if evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must include a timezone")

        spread = quote.ask - quote.bid
        mid = (quote.ask + quote.bid) / Decimal("2")
        spread_pct = spread / mid * Decimal("100")
        age_seconds = Decimal(str((evaluated_at - quote.source_timestamp).total_seconds()))
        reasons: list[str] = []
        status = MarketDataStatus.VALID

        if spread < 0:
            status = MarketDataStatus.INVALID
            reasons.append("ask price is below bid price")
        if age_seconds > policy.maximum_age_seconds:
            status = MarketDataStatus.STALE
            reasons.append("quote exceeds the configured maximum age")
        if age_seconds < -policy.maximum_future_skew_seconds:
            status = MarketDataStatus.INVALID
            reasons.append("source timestamp is too far in the future")
        if spread_pct > policy.maximum_spread_pct:
            status = MarketDataStatus.INVALID
            reasons.append("spread exceeds the configured sanity limit")
        if previous_mid is not None:
            jump_pct = abs(mid - previous_mid) / previous_mid * Decimal("100")
            if jump_pct > policy.maximum_price_jump_pct:
                status = MarketDataStatus.INVALID
                reasons.append("price jump exceeds the configured sanity limit")
        if not reasons:
            reasons.append("quote passed freshness and price sanity checks")

        return QuoteAssessment(
            status=status,
            mid=mid,
            spread=spread,
            spread_pct=spread_pct,
            age_seconds=age_seconds,
            reasons=reasons,
        )
