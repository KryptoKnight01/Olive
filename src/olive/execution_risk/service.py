from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.execution_risk.engine import ExecutionRiskEngine
from olive.execution_risk.models import ExecutionRiskDecisionRecord, ExecutionRiskPolicyRecord
from olive.execution_risk.schemas import ExecutionRiskInput, ExecutionRiskPolicy
from olive.market_data.models import MarketQuoteRecord


class ExecutionRiskError(ValueError):
    pass


class ExecutionRiskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self,
        market_quote_id: uuid.UUID,
        request: ExecutionRiskInput,
        *,
        configuration_version: str,
    ) -> ExecutionRiskDecisionRecord:
        quote = await self._session.get(MarketQuoteRecord, market_quote_id)
        if quote is None:
            raise ExecutionRiskError("market quote was not found")
        policy_record = await self._session.scalar(
            select(ExecutionRiskPolicyRecord).where(
                ExecutionRiskPolicyRecord.configuration_version == configuration_version
            )
        )
        if policy_record is None:
            raise ExecutionRiskError("execution risk policy is not configured")
        decision = ExecutionRiskEngine().evaluate(
            request, ExecutionRiskPolicy.model_validate(policy_record.parameters)
        )
        result = ExecutionRiskDecisionRecord(
            market_quote_id=quote.id,
            execution_risk_policy_id=policy_record.id,
            signal_id=decision.signal_id,
            action=decision.action.value,
            requested_quantity=decision.requested_quantity,
            approved_quantity=decision.approved_quantity,
            requested_notional=decision.requested_notional,
            approved_notional=decision.approved_notional,
            maximum_executable_notional=decision.maximum_executable_notional,
            slice_count=decision.slice_count,
            binding_limits=decision.binding_limits,
            reasons=decision.reasons,
        )
        self._session.add(result)
        await self._session.commit()
        return result
