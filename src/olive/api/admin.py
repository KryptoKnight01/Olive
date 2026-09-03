from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.db import get_session
from olive.domain.models import Strategy, StrategyVersion
from olive.gateway.models import SignalIntakeRecord
from olive.governance.auth import AdminViewerDependency
from olive.governance.models import KillSwitchRecord
from olive.governance.schemas import (
    AdminSnapshot,
    PaperExecutionMonitor,
    PaperExecutionMonitorItem,
    PaperExecutionSummary,
    StrategyPaperSummary,
)
from olive.paper.models import PaperOrderRecord, PaperPipelineRunRecord, PaperPositionRecord
from olive.readiness.engine import LiveReadinessEngine
from olive.readiness.schemas import PerformanceMetrics, PerformanceThresholds
from olive.risk.models import TradeRiskDecisionRecord

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def _strategy_summaries(rows: list[Any]) -> list[StrategyPaperSummary]:
    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for strategy_code, strategy_version, run, intake, risk in rows:
        grouped[(strategy_code, strategy_version)].append((run, intake, risk))

    thresholds = PerformanceThresholds()
    engine = LiveReadinessEngine()
    summaries: list[StrategyPaperSummary] = []
    for (code, version), trades in sorted(grouped.items()):
        trades.sort(key=lambda item: item[0].created_at)
        pnls = [Decimal(str(item[0].realized_pnl)) for item in trades]
        winners = sum(pnl > 0 for pnl in pnls)
        gross_profit = sum((pnl for pnl in pnls if pnl > 0), Decimal("0"))
        gross_loss = abs(sum((pnl for pnl in pnls if pnl < 0), Decimal("0")))
        profit_factor = gross_profit / gross_loss if gross_loss else None

        r_values: list[Decimal] = []
        for run, intake, risk in trades:
            if risk and intake.entry_price is not None and intake.stop_price is not None:
                initial_risk = abs(
                    Decimal(str(intake.entry_price)) - Decimal(str(intake.stop_price))
                ) * Decimal(str(risk.position_size))
                if initial_risk > 0:
                    r_values.append(Decimal(str(run.realized_pnl)) / initial_risk)
        average_r = (
            sum(r_values, Decimal("0")) / Decimal(len(r_values)) if r_values else Decimal("0")
        )

        starting_equity = next(
            (Decimal(str(risk.equity_snapshot)) for _, _, risk in trades if risk), Decimal("0")
        )
        equity = peak = starting_equity
        max_drawdown = Decimal("0")
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - equity) / peak * Decimal("100"))

        win_rate = Decimal(winners) / Decimal(len(trades)) * Decimal("100")
        assessment = engine.assess_performance(
            PerformanceMetrics(
                strategy_key=f"{code}:{version}",
                profit_factor=(
                    profit_factor
                    if profit_factor is not None
                    else (thresholds.min_profit_factor if gross_profit > 0 else Decimal("0"))
                ),
                win_rate=win_rate,
                expectancy_r=average_r,
                average_r=average_r,
                max_drawdown_pct=max_drawdown,
                trades=len(trades),
            ),
            thresholds,
        )
        summaries.append(
            StrategyPaperSummary(
                strategy_code=code,
                strategy_version=version,
                total_executions=len(trades),
                filled_executions=sum(item[0].order_status == "FILLED" for item in trades),
                protected_executions=sum(
                    item[0].protection_status == "PROTECTED" for item in trades
                ),
                reconciled_executions=sum(item[0].reconciled for item in trades),
                total_realized_pnl=sum(pnls, Decimal("0")),
                latest_execution_at=max(item[0].created_at for item in trades),
                winning_executions=winners,
                win_rate_pct=win_rate,
                profit_factor=profit_factor,
                average_r=average_r,
                max_drawdown_pct=max_drawdown,
                health_status=assessment.status.value,
                health_breaches=list(assessment.breaches),
            )
        )
    return summaries


@router.get("/command-center", response_model=AdminSnapshot)
async def command_center(
    session: SessionDependency, _principal: AdminViewerDependency
) -> AdminSnapshot:
    positions = await session.scalar(
        select(func.count())
        .select_from(PaperPositionRecord)
        .where(PaperPositionRecord.quantity != 0)
    )
    orders = await session.scalar(
        select(func.count())
        .select_from(PaperOrderRecord)
        .where(PaperOrderRecord.status.in_(["NEW", "PARTIALLY_FILLED"]))
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
    performance_rows = (
        await session.execute(
            select(
                Strategy.code,
                StrategyVersion.version,
                PaperPipelineRunRecord,
                SignalIntakeRecord,
                TradeRiskDecisionRecord,
            )
            .join(
                SignalIntakeRecord,
                SignalIntakeRecord.signal_id == PaperPipelineRunRecord.signal_id,
            )
            .join(StrategyVersion, StrategyVersion.id == SignalIntakeRecord.strategy_version_id)
            .join(Strategy, Strategy.id == StrategyVersion.strategy_id)
            .outerjoin(
                TradeRiskDecisionRecord,
                TradeRiskDecisionRecord.signal_intake_id == SignalIntakeRecord.id,
            )
            .order_by(Strategy.code, StrategyVersion.version, PaperPipelineRunRecord.created_at)
        )
    ).all()
    return PaperExecutionMonitor(
        summary=PaperExecutionSummary(
            total_executions=summary_row[0],
            filled_executions=summary_row[1],
            protected_executions=summary_row[2],
            reconciled_executions=summary_row[3],
            total_realized_pnl=summary_row[4],
            latest_execution_at=summary_row[5],
        ),
        strategies=_strategy_summaries(list(performance_rows)),
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
