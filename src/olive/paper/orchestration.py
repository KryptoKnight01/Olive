from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.config import AppEnvironment, Settings
from olive.domain.models import VenueInstrument
from olive.gateway.models import SignalDirection, SignalIntakeRecord, SignalIntakeStatus
from olive.gateway.schemas import PaperExecutionResponse
from olive.paper.models import PaperPipelineRunRecord
from olive.paper.oms import PaperOms
from olive.paper.pipeline import PaperPipeline
from olive.paper.sandbox import FirstVenueSandboxConnector
from olive.risk.schemas import RiskDecisionOutcome
from olive.risk.service import RiskEvaluationError, SingleTradeRiskService


class AutomaticPaperOrchestrator:
    """Fail-closed bridge from validated signal intake to deterministic paper execution."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def execute(self, intake_id: uuid.UUID) -> PaperExecutionResponse:
        if not self._settings.paper_auto_execute:
            return PaperExecutionResponse(outcome="DISABLED", risk_decision="NOT_RUN")
        if self._settings.app_env not in {AppEnvironment.PAPER, AppEnvironment.STAGING}:
            return PaperExecutionResponse(
                outcome="BLOCKED",
                risk_decision="NOT_RUN",
                reason="automatic paper execution is restricted to paper and staging",
            )

        intake = await self._session.scalar(
            select(SignalIntakeRecord).where(SignalIntakeRecord.id == intake_id)
        )
        if intake is None or intake.status is not SignalIntakeStatus.RISK_REVIEW:
            return PaperExecutionResponse(
                outcome="BLOCKED",
                risk_decision="NOT_RUN",
                reason="signal is not eligible for risk review",
            )
        if (
            intake.signal_id is None
            or intake.venue_instrument_id is None
            or intake.entry_price is None
            or not intake.targets
        ):
            return await self._record_failure(intake, "validated signal is incomplete")
        if intake.direction is not SignalDirection.LONG:
            return await self._record_failure(
                intake, "automatic paper execution currently supports LONG signals only"
            )
        mapping = await self._session.get(VenueInstrument, intake.venue_instrument_id)
        if mapping is None:
            return await self._record_failure(intake, "venue instrument mapping is missing")

        try:
            risk = await SingleTradeRiskService(self._session).evaluate(
                intake.id,
                equity=self._settings.paper_equity,
                available_margin=self._settings.paper_available_margin,
                requested_risk_pct=self._settings.paper_requested_risk_pct,
            )
        except RiskEvaluationError as exc:
            return await self._record_failure(intake, str(exc))
        if risk.decision == RiskDecisionOutcome.REJECTED.value or risk.position_size <= 0:
            return await self._record_failure(
                intake,
                "; ".join(risk.reasons) or "single-trade risk rejected the signal",
                risk_decision=risk.decision,
            )

        oms = PaperOms(fee_rate=self._settings.paper_fee_rate)
        pipeline = PaperPipeline(
            oms,
            FirstVenueSandboxConnector(oms, balance=self._settings.paper_equity),
        )
        try:
            result = pipeline.execute_round_trip(
                signal_id=intake.signal_id,
                instrument_id=mapping.instrument_id,
                quantity=risk.position_size,
                entry_price=intake.entry_price,
                exit_price=Decimal(intake.targets[0]),
            )
        except (RuntimeError, ValueError, ConnectionError) as exc:
            return await self._record_failure(
                intake, str(exc), risk_decision=risk.decision
            )

        self._session.add(
            PaperPipelineRunRecord(
                signal_id=result.signal_id,
                order_id=result.order_id,
                order_status=result.order_status.value,
                protection_status=result.protection_status.value,
                reconciled=result.reconciled,
                realized_pnl=result.realized_pnl,
            )
        )
        intake.validation_details = {
            **(intake.validation_details or {}),
            "paper_execution": {
                "outcome": "EXECUTED",
                "risk_decision": risk.decision,
                "order_id": str(result.order_id),
                "order_status": result.order_status.value,
                "protection_status": result.protection_status.value,
                "reconciled": result.reconciled,
                "realized_pnl": str(result.realized_pnl),
            },
        }
        await self._session.commit()
        return PaperExecutionResponse(
            outcome="EXECUTED",
            risk_decision=risk.decision,
            order_id=result.order_id,
            order_status=result.order_status.value,
            protection_status=result.protection_status.value,
            reconciled=result.reconciled,
            realized_pnl=result.realized_pnl,
        )

    async def _record_failure(
        self,
        intake: SignalIntakeRecord,
        reason: str,
        *,
        risk_decision: str = "NOT_RUN",
    ) -> PaperExecutionResponse:
        intake.validation_details = {
            **(intake.validation_details or {}),
            "paper_execution": {
                "outcome": "REJECTED",
                "risk_decision": risk_decision,
                "reason": reason,
            },
        }
        await self._session.commit()
        return PaperExecutionResponse(
            outcome="REJECTED", risk_decision=risk_decision, reason=reason
        )
