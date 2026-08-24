from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from olive.domain.models import VenueInstrument
from olive.gateway.models import SignalIntakeRecord, SignalIntakeStatus
from olive.risk.engine import SingleTradeRiskEngine
from olive.risk.hierarchy import HierarchicalExposureEngine
from olive.risk.models import (
    HierarchicalExposureLimitRecord,
    HierarchicalRiskDecisionRecord,
    PortfolioRiskDecisionRecord,
    PortfolioRiskPolicyRecord,
    SingleTradeRiskPolicyRecord,
    TradeRiskDecisionRecord,
)
from olive.risk.portfolio import PortfolioRiskEngine
from olive.risk.schemas import (
    ExposureDimension,
    ExposureMetric,
    HierarchicalExposureLimit,
    HierarchicalRiskInput,
    PortfolioRiskInput,
    PortfolioRiskPolicy,
    SingleTradeRiskInput,
    SingleTradeRiskPolicy,
)


class RiskEvaluationError(Exception):
    pass


class SingleTradeRiskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self,
        intake_id: uuid.UUID,
        *,
        equity: Decimal,
        available_margin: Decimal,
        requested_risk_pct: Decimal,
    ) -> TradeRiskDecisionRecord:
        intake = await self._session.scalar(
            select(SignalIntakeRecord)
            .options(
                joinedload(SignalIntakeRecord.strategy_version),
                joinedload(SignalIntakeRecord.venue_instrument).joinedload(
                    VenueInstrument.instrument
                ),
            )
            .where(SignalIntakeRecord.id == intake_id)
        )
        if intake is None or intake.status is not SignalIntakeStatus.RISK_REVIEW:
            raise RiskEvaluationError("signal is not eligible for risk review")
        if intake.strategy_version_id is None or intake.venue_instrument is None:
            raise RiskEvaluationError("validated signal is missing canonical references")
        instrument = intake.venue_instrument.instrument
        policy_record = await self._session.scalar(
            select(SingleTradeRiskPolicyRecord).where(
                SingleTradeRiskPolicyRecord.strategy_version_id == intake.strategy_version_id
            )
        )
        if policy_record is None:
            raise RiskEvaluationError("single-trade risk policy is not configured")
        if intake.signal_id is None or intake.entry_price is None or intake.stop_price is None:
            raise RiskEvaluationError("validated signal is missing risk inputs")

        decision = SingleTradeRiskEngine().evaluate(
            SingleTradeRiskInput(
                signal_id=intake.signal_id,
                equity=equity,
                available_margin=available_margin,
                entry_price=intake.entry_price,
                stop_price=intake.stop_price,
                requested_risk_pct=requested_risk_pct,
                contract_multiplier=instrument.contract_multiplier,
                lot_size=instrument.lot_size,
                instrument_max_leverage=instrument.max_leverage,
            ),
            SingleTradeRiskPolicy(
                base_risk_pct=policy_record.base_risk_pct,
                max_risk_pct=policy_record.max_risk_pct,
                max_notional=policy_record.max_notional,
                max_leverage=policy_record.max_leverage,
                max_margin=policy_record.max_margin,
                min_stop_distance_pct=policy_record.min_stop_distance_pct,
                max_stop_distance_pct=policy_record.max_stop_distance_pct,
            ),
        )
        record = TradeRiskDecisionRecord(
            signal_intake_id=intake.id,
            decision=decision.decision.value,
            requested_risk_pct=decision.requested_risk_pct,
            approved_risk_pct=decision.approved_risk_pct,
            position_size=decision.position_size,
            base_risk_pct=decision.base_risk_pct,
            equity_snapshot=equity,
            available_margin_snapshot=available_margin,
            multipliers={key: str(value) for key, value in decision.multipliers.items()},
            limits={
                key: None if value is None else str(value) for key, value in decision.limits.items()
            },
            reasons=decision.reasons,
        )
        self._session.add(record)
        await self._session.commit()
        return record


class PortfolioRiskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self,
        trade_risk_decision_id: uuid.UUID,
        request: PortfolioRiskInput,
        *,
        scope_key: str = "default",
    ) -> PortfolioRiskDecisionRecord:
        trade_decision = await self._session.get(
            TradeRiskDecisionRecord, trade_risk_decision_id
        )
        if trade_decision is None:
            raise RiskEvaluationError("single-trade risk decision was not found")
        policy_record = await self._session.scalar(
            select(PortfolioRiskPolicyRecord).where(
                PortfolioRiskPolicyRecord.scope_key == scope_key
            )
        )
        if policy_record is None:
            raise RiskEvaluationError("portfolio risk policy is not configured")

        decision = PortfolioRiskEngine().evaluate(
            request,
            PortfolioRiskPolicy(
                max_gross_exposure_pct=policy_record.max_gross_exposure_pct,
                max_net_exposure_pct=policy_record.max_net_exposure_pct,
                max_long_exposure_pct=policy_record.max_long_exposure_pct,
                max_short_exposure_pct=policy_record.max_short_exposure_pct,
                max_open_stop_risk_pct=policy_record.max_open_stop_risk_pct,
                max_margin_utilization_pct=policy_record.max_margin_utilization_pct,
                max_leverage=policy_record.max_leverage,
                max_concurrent_positions=policy_record.max_concurrent_positions,
            ),
        )
        record = PortfolioRiskDecisionRecord(
            trade_risk_decision_id=trade_decision.id,
            portfolio_risk_policy_id=policy_record.id,
            decision=decision.decision.value,
            approved_fraction=decision.approved_fraction,
            approved_notional=decision.approved_notional,
            current_snapshot=self._json_metrics(decision.current),
            projected_snapshot=self._json_metrics(decision.projected),
            limits=self._json_metrics(decision.limits),
            reasons=decision.reasons,
        )
        self._session.add(record)
        await self._session.commit()
        return record

    @staticmethod
    def _json_metrics(values: dict[str, Decimal | int]) -> dict[str, str | int]:
        return {
            key: value if isinstance(value, int) else str(value) for key, value in values.items()
        }


class HierarchicalRiskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self,
        portfolio_risk_decision_id: uuid.UUID,
        request: HierarchicalRiskInput,
        *,
        configuration_version: str,
    ) -> HierarchicalRiskDecisionRecord:
        portfolio_decision = await self._session.get(
            PortfolioRiskDecisionRecord, portfolio_risk_decision_id
        )
        if portfolio_decision is None:
            raise RiskEvaluationError("portfolio risk decision was not found")
        records = (
            await self._session.scalars(
                select(HierarchicalExposureLimitRecord).where(
                    HierarchicalExposureLimitRecord.configuration_version
                    == configuration_version,
                    HierarchicalExposureLimitRecord.enabled.is_(True),
                )
            )
        ).all()
        if not records:
            raise RiskEvaluationError("hierarchical exposure limits are not configured")
        limits = tuple(
            HierarchicalExposureLimit(
                dimension=ExposureDimension(record.dimension),
                scope_key=record.scope_key,
                metric=ExposureMetric(record.metric),
                maximum=record.maximum,
            )
            for record in records
        )
        decision = HierarchicalExposureEngine().evaluate(request, limits)
        result = HierarchicalRiskDecisionRecord(
            portfolio_risk_decision_id=portfolio_decision.id,
            configuration_version=configuration_version,
            decision=decision.decision.value,
            approved_fraction=decision.approved_fraction,
            approved_notional=decision.approved_notional,
            binding_limit=decision.binding_limit,
            evaluations=decision.evaluations,
            reasons=decision.reasons,
        )
        self._session.add(result)
        await self._session.commit()
        return result
