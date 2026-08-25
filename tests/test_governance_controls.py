from __future__ import annotations

import uuid

import pytest

from olive.governance.engine import AuthorizationError, ConfigurationError, GovernanceEngine
from olive.governance.schemas import (
    ConfigurationChange,
    KillSwitchAction,
    KillSwitchCommand,
    KillSwitchScope,
    Permission,
    Role,
)


def test_viewer_cannot_trade() -> None:
    with pytest.raises(AuthorizationError):
        GovernanceEngine.authorize(Role.VIEWER, Permission.TRADE)


def test_trader_can_trade_but_cannot_change_configuration() -> None:
    GovernanceEngine.authorize(Role.TRADER, Permission.TRADE)
    with pytest.raises(AuthorizationError):
        GovernanceEngine.authorize(Role.TRADER, Permission.MANAGE_CONFIG)


def test_risk_increase_requires_distinct_approver() -> None:
    actor = uuid.uuid4()
    change = ConfigurationChange(
        namespace="risk",
        version="2",
        values={"max_risk": "2"},
        increases_risk=True,
        requested_by=actor,
        approved_by=actor,
    )
    with pytest.raises(ConfigurationError, match="dual approval"):
        GovernanceEngine().publish_configuration(change, Role.ADMIN)


def test_configuration_versions_are_immutable() -> None:
    change = ConfigurationChange(
        namespace="risk",
        version="1",
        values={"max_risk": "1"},
        increases_risk=False,
        requested_by=uuid.uuid4(),
    )
    engine = GovernanceEngine()
    engine.publish_configuration(change, Role.ADMIN)
    with pytest.raises(ConfigurationError, match="immutable"):
        engine.publish_configuration(change, Role.ADMIN)


def test_risk_manager_can_pause_strategy_entries() -> None:
    engine = GovernanceEngine()
    command = KillSwitchCommand(
        scope=KillSwitchScope.STRATEGY,
        scope_key="OLC",
        action=KillSwitchAction.PAUSE_ENTRIES,
        reason="manual risk review",
        actor_id=uuid.uuid4(),
    )
    state = engine.activate_kill_switch(command, Role.RISK_MANAGER)
    assert state.active
    assert not engine.permits_new_entry({"STRATEGY": "OLC"})
    assert engine.permits_new_entry({"STRATEGY": "OTHER"})


def test_risk_manager_cannot_trigger_global_emergency_halt() -> None:
    command = KillSwitchCommand(
        scope=KillSwitchScope.GLOBAL,
        scope_key="*",
        action=KillSwitchAction.EMERGENCY_HALT,
        reason="incident",
        actor_id=uuid.uuid4(),
    )
    with pytest.raises(AuthorizationError, match="administrator"):
        GovernanceEngine().activate_kill_switch(command, Role.RISK_MANAGER)


def test_audit_reconstructs_configuration_action() -> None:
    change = ConfigurationChange(
        namespace="execution",
        version="1",
        values={"enabled": True},
        increases_risk=False,
        requested_by=uuid.uuid4(),
    )
    engine = GovernanceEngine()
    engine.publish_configuration(change, Role.SUPER_ADMIN)
    events = engine.reconstruct("execution:1")
    assert len(events) == 1
    assert events[0].action == "CONFIGURATION_PUBLISHED"
