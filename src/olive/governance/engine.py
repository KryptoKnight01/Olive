from __future__ import annotations

import uuid
from datetime import UTC, datetime

from olive.governance.schemas import (
    ROLE_PERMISSIONS,
    AuditEvent,
    ConfigurationChange,
    KillSwitchAction,
    KillSwitchCommand,
    KillSwitchState,
    Permission,
    Role,
)


class AuthorizationError(PermissionError):
    pass


class ConfigurationError(ValueError):
    pass


class GovernanceEngine:
    def __init__(self) -> None:
        self.configurations: dict[tuple[str, str], ConfigurationChange] = {}
        self.audit_events: list[AuditEvent] = []
        self.kill_switches: dict[tuple[str, str], KillSwitchState] = {}

    @staticmethod
    def authorize(role: Role, permission: Permission) -> None:
        if permission not in ROLE_PERMISSIONS[role]:
            raise AuthorizationError(f"{role.value} lacks {permission.value}")

    def publish_configuration(self, change: ConfigurationChange, role: Role) -> None:
        self.authorize(role, Permission.MANAGE_CONFIG)
        key = (change.namespace, change.version)
        if key in self.configurations:
            raise ConfigurationError("configuration versions are immutable")
        if change.increases_risk and (
            change.approved_by is None or change.approved_by == change.requested_by
        ):
            raise ConfigurationError("risk-increasing configuration requires dual approval")
        self.configurations[key] = change
        self._audit(
            change.requested_by,
            "CONFIGURATION_PUBLISHED",
            "configuration",
            f"{change.namespace}:{change.version}",
            {"increases_risk": change.increases_risk},
        )

    def activate_kill_switch(self, command: KillSwitchCommand, role: Role) -> KillSwitchState:
        self.authorize(role, Permission.OPERATE_KILL_SWITCH)
        if command.action is KillSwitchAction.EMERGENCY_HALT and role not in {
            Role.ADMIN,
            Role.SUPER_ADMIN,
        }:
            raise AuthorizationError("global emergency halt requires an administrator")
        state = KillSwitchState(
            state_id=uuid.uuid4(),
            scope=command.scope,
            scope_key=command.scope_key,
            action=command.action,
            active=True,
            reason=command.reason,
            actor_id=command.actor_id,
        )
        self.kill_switches[(command.scope.value, command.scope_key)] = state
        self._audit(
            command.actor_id,
            "KILL_SWITCH_ACTIVATED",
            "kill_switch",
            str(state.state_id),
            {"scope": command.scope.value, "action": command.action.value},
        )
        return state

    def permits_new_entry(self, dimensions: dict[str, str]) -> bool:
        for state in self.kill_switches.values():
            if not state.active:
                continue
            if (
                state.scope.value == "GLOBAL"
                or dimensions.get(state.scope.value) == state.scope_key
            ):
                return False
        return True

    def reconstruct(self, resource_id: str) -> list[AuditEvent]:
        return [event for event in self.audit_events if event.resource_id == resource_id]

    def _audit(
        self,
        actor_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, str | int | bool],
    ) -> None:
        self.audit_events.append(
            AuditEvent(
                event_id=uuid.uuid4(),
                occurred_at=datetime.now(UTC),
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            )
        )
