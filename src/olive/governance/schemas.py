from __future__ import annotations

import uuid
from datetime import datetime
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
