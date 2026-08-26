from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from olive.config import Settings, get_settings
from olive.governance.engine import AuthorizationError, GovernanceEngine
from olive.governance.schemas import Permission, Role


@dataclass(frozen=True)
class AdminPrincipal:
    role: Role


SettingsDependency = Annotated[Settings, Depends(get_settings)]


async def require_admin_viewer(
    settings: SettingsDependency,
    authorization: Annotated[str | None, Header()] = None,
) -> AdminPrincipal:
    configured = settings.admin_api_key
    if configured is None or not configured.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin authentication is not configured",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="admin bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    supplied = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(supplied, configured.get_secret_value()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="admin bearer token is invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        GovernanceEngine.authorize(settings.admin_api_role, Permission.VIEW)
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role lacks view permission",
        ) from exc
    return AdminPrincipal(role=settings.admin_api_role)


AdminViewerDependency = Annotated[AdminPrincipal, Depends(require_admin_viewer)]
