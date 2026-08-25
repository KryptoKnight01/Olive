from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from olive.db import Base
from olive.domain.models import TimestampMixin, UuidMixin


class UserRoleRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    session_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConfigurationVersionRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "configuration_versions"
    __table_args__ = (
        UniqueConstraint("namespace", "version", name="uq_configuration_namespace_version"),
    )
    namespace: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    values: Mapped[dict[str, str | int | bool]] = mapped_column(JSON, nullable=False)
    increases_risk: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column()


class AuditEventRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "audit_events"
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[dict[str, str | int | bool]] = mapped_column(JSON, nullable=False)


class KillSwitchRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "kill_switches"
    __table_args__ = (UniqueConstraint("scope", "scope_key", name="uq_kill_switch_scope"),)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
