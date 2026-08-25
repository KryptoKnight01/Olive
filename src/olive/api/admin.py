from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.db import get_session
from olive.gateway.models import SignalIntakeRecord
from olive.governance.models import KillSwitchRecord
from olive.governance.schemas import AdminSnapshot
from olive.paper.models import PaperOrderRecord, PaperPositionRecord

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/command-center", response_model=AdminSnapshot)
async def command_center(session: SessionDependency) -> AdminSnapshot:
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
