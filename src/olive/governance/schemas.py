from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    TRADER = "TRADER"
    RISK_MANAGER = "RISK_MANAGER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class Permission(StrEnum):
    VIEW = "VIEW"
    TRADE = "TRADE"
    MANAGE_RISK = "MANAGE_RISK"
    MANAGE_CONFIG = "MANAGE_CONFIG"
    MANAGE_USERS = "MANAGE_USERS"
    OPERATE_KILL_SWITCH = "OPERATE_KILL_SWITCH"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.VIEW}),
    Role.ANALYST: frozenset({Permission.VIEW}),
    Role.TRADER: frozenset({Permission.VIEW, Permission.TRADE}),
    Role.RISK_MANAGER: frozenset(
        {Permission.VIEW, Permission.MANAGE_RISK, Permission.OPERATE_KILL_SWITCH}
    ),
    Role.ADMIN: frozenset(
        {
            Permission.VIEW,
            Permission.TRADE,
            Permission.MANAGE_CONFIG,
            Permission.MANAGE_USERS,
            Permission.OPERATE_KILL_SWITCH,
        }
    ),
    Role.SUPER_ADMIN: frozenset(Permission),
}


class ConfigurationChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    values: dict[str, str | int | bool]
    increases_risk: bool
    requested_by: uuid.UUID
    approved_by: uuid.UUID | None = None


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: uuid.UUID
    occurred_at: datetime
    actor_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, str | int | bool]


class KillSwitchScope(StrEnum):
    GLOBAL = "GLOBAL"
    STRATEGY = "STRATEGY"
    ASSET = "ASSET"
    ASSET_CLASS = "ASSET_CLASS"
    ACCOUNT = "ACCOUNT"
    VENUE = "VENUE"


class KillSwitchAction(StrEnum):
    PAUSE_ENTRIES = "PAUSE_ENTRIES"
    CANCEL_ORDERS = "CANCEL_ORDERS"
    CLOSE_POSITIONS = "CLOSE_POSITIONS"
    EMERGENCY_HALT = "EMERGENCY_HALT"


class KillSwitchCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope: KillSwitchScope
    scope_key: str
    action: KillSwitchAction
    reason: str = Field(min_length=1)
    actor_id: uuid.UUID


class KillSwitchState(BaseModel):
    model_config = ConfigDict(frozen=True)

    state_id: uuid.UUID
    scope: KillSwitchScope
    scope_key: str
    action: KillSwitchAction
    active: bool
    reason: str
    actor_id: uuid.UUID


class AdminSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    health: str
    open_positions: int
    open_orders: int
    active_signals: int
    active_kill_switches: int
    gross_exposure: str
    net_exposure: str
    open_risk: str
    margin_utilization: str


class PaperExecutionMonitorItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    pipeline_run_id: uuid.UUID
    created_at: datetime
    signal_id: uuid.UUID
    intake_id: uuid.UUID
    signal_status: str
    environment: str | None
    direction: str | None
    instrument_mapping_id: uuid.UUID | None
    entry_price: Decimal | None
    stop_price: Decimal | None
    targets: list[str]
    risk_decision: str | None
    requested_risk_pct: Decimal | None
    approved_risk_pct: Decimal | None
    position_size: Decimal | None
    order_id: uuid.UUID
    order_status: str
    protection_status: str
    reconciled: bool
    realized_pnl: Decimal


class PaperExecutionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_executions: int
    filled_executions: int
    protected_executions: int
    reconciled_executions: int
    total_realized_pnl: Decimal
    latest_execution_at: datetime | None


class StrategyPaperSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_code: str
    strategy_version: str
    total_executions: int
    filled_executions: int
    protected_executions: int
    reconciled_executions: int
    total_realized_pnl: Decimal
    latest_execution_at: datetime | None
    winning_executions: int
    win_rate_pct: Decimal
    profit_factor: Decimal | None
    average_r: Decimal
    max_drawdown_pct: Decimal
    health_status: str
    health_breaches: list[str]


class PaperExecutionMonitor(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: PaperExecutionSummary
    strategies: list[StrategyPaperSummary]
    executions: list[PaperExecutionMonitorItem]
