from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from olive.config import Settings, get_settings
from olive.health import DependencyStatus, HealthChecker

router = APIRouter(prefix="/health", tags=["health"])

SettingsDependency = Annotated[Settings, Depends(get_settings)]


class LiveResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class DependencyResponse(BaseModel):
    status: str
    detail: str | None = None


class ReadyResponse(BaseModel):
    status: str
    dependencies: dict[str, DependencyResponse]


def get_health_checker(request: Request) -> HealthChecker:
    return cast(HealthChecker, request.app.state.health_checker)


@router.get("/live", response_model=LiveResponse)
async def live(settings: SettingsDependency) -> LiveResponse:
    return LiveResponse(
        status="up",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    response: Response,
    checker: Annotated[HealthChecker, Depends(get_health_checker)],
) -> ReadyResponse:
    checks = await checker.check()
    is_ready = all(check.status == "up" for check in checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ready" if is_ready else "not_ready",
        dependencies={name: _dependency_response(check) for name, check in checks.items()},
    )


def _dependency_response(check: DependencyStatus) -> DependencyResponse:
    return DependencyResponse(status=check.status, detail=check.detail)
