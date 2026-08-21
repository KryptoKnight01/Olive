from __future__ import annotations

from httpx import AsyncClient

from olive.api.health import get_health_checker
from olive.health import DependencyStatus
from olive.main import app


class FakeHealthChecker:
    def __init__(self, statuses: dict[str, DependencyStatus]) -> None:
        self._statuses = statuses

    async def check(self) -> dict[str, DependencyStatus]:
        return self._statuses


async def test_liveness_does_not_require_dependencies(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "up"


async def test_readiness_is_ready_when_all_dependencies_are_up(client: AsyncClient) -> None:
    app.dependency_overrides[get_health_checker] = lambda: FakeHealthChecker(
        {"postgres": DependencyStatus("up"), "redis": DependencyStatus("up")}
    )
    try:
        response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_health_checker, None)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "postgres": {"status": "up", "detail": None},
            "redis": {"status": "up", "detail": None},
        },
    }


async def test_readiness_fails_closed_when_dependency_is_down(client: AsyncClient) -> None:
    app.dependency_overrides[get_health_checker] = lambda: FakeHealthChecker(
        {
            "postgres": DependencyStatus("up"),
            "redis": DependencyStatus("down", "TimeoutError"),
        }
    )
    try:
        response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_health_checker, None)

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["dependencies"]["redis"] == {
        "status": "down",
        "detail": "TimeoutError",
    }
