from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.db import get_session
from olive.gateway.models import SignalIntakeRecord
from olive.governance.auth import AdminViewerDependency
from olive.governance.models import KillSwitchRecord
from olive.governance.schemas import (
    AdminSnapshot,
    PaperExecutionMonitor,
    PaperExecutionMonitorItem,
    PaperExecutionSummary,
)
from olive.paper.models import PaperOrderRecord, PaperPipelineRunRecord, PaperPositionRecord
from olive.risk.models import TradeRiskDecisionRecord

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/command-center", response_model=AdminSnapshot)
async def command_center(
    session: SessionDependency, _principal: AdminViewerDependency
) -> AdminSnapshot:
    positions = await session.scalar(
        select(func.count()).select_from(PaperPositionRecord).where(
            PaperPositionRecord.quantity != 0
        )
    )
    orders = await session.scalar(
        select(func.count()).select_from(PaperOrderRecord).where(
            PaperOrderRecord.status.in_(["NEW", "PARTIALLY_FILLED"])
        )
    )
    signals = await session.scalar(select(func.count()).select_from(SignalIntakeRecord))
    switches = await session.scalar(
        select(func.count()).select_from(KillSwitchRecord).where(KillSwitchRecord.active.is_(True))
    )
    return AdminSnapshot(
        health="HEALTHY",
        open_positions=positions or 0,
        open_orders=orders or 0,
        active_signals=signals or 0,
        active_kill_switches=switches or 0,
        gross_exposure="0",
        net_exposure="0",
        open_risk="0",
        margin_utilization="0",
    )


@router.get("/paper-executions", response_model=PaperExecutionMonitor)
async def paper_executions(
    session: SessionDependency,
    _principal: AdminViewerDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PaperExecutionMonitor:
    rows = (
        await session.execute(
            select(PaperPipelineRunRecord, SignalIntakeRecord, TradeRiskDecisionRecord)
            .join(
                SignalIntakeRecord,
                SignalIntakeRecord.signal_id == PaperPipelineRunRecord.signal_id,
            )
            .outerjoin(
                TradeRiskDecisionRecord,
                TradeRiskDecisionRecord.signal_intake_id == SignalIntakeRecord.id,
            )
            .order_by(PaperPipelineRunRecord.created_at.desc())
            .limit(limit)
        )
    ).all()
    summary_row = (
        await session.execute(
            select(
                func.count(PaperPipelineRunRecord.id),
                func.count(PaperPipelineRunRecord.id).filter(
                    PaperPipelineRunRecord.order_status == "FILLED"
                ),
                func.count(PaperPipelineRunRecord.id).filter(
                    PaperPipelineRunRecord.protection_status == "PROTECTED"
                ),
                func.count(PaperPipelineRunRecord.id).filter(
                    PaperPipelineRunRecord.reconciled.is_(True)
                ),
                func.coalesce(func.sum(PaperPipelineRunRecord.realized_pnl), 0),
                func.max(PaperPipelineRunRecord.created_at),
            )
        )
    ).one()
    return PaperExecutionMonitor(
        summary=PaperExecutionSummary(
            total_executions=summary_row[0],
            filled_executions=summary_row[1],
            protected_executions=summary_row[2],
            reconciled_executions=summary_row[3],
            total_realized_pnl=summary_row[4],
            latest_execution_at=summary_row[5],
        ),
        executions=[
            PaperExecutionMonitorItem(
                pipeline_run_id=run.id,
                created_at=run.created_at,
                signal_id=run.signal_id,
                intake_id=intake.id,
                signal_status=intake.status.value,
                environment=intake.environment.value if intake.environment else None,
                direction=intake.direction.value if intake.direction else None,
                instrument_mapping_id=intake.venue_instrument_id,
                entry_price=intake.entry_price,
                stop_price=intake.stop_price,
                targets=intake.targets or [],
                risk_decision=risk.decision if risk else None,
                requested_risk_pct=risk.requested_risk_pct if risk else None,
                approved_risk_pct=risk.approved_risk_pct if risk else None,
                position_size=risk.position_size if risk else None,
                order_id=run.order_id,
                order_status=run.order_status,
                protection_status=run.protection_status,
                reconciled=run.reconciled,
                realized_pnl=run.realized_pnl,
            )
            for run, intake, risk in rows
        ],
    )
