from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True)
class DependencyStatus:
    status: str
    detail: str | None = None


class HealthChecker(Protocol):
    async def check(self) -> dict[str, DependencyStatus]: ...


class InfrastructureHealthChecker:
    def __init__(self, engine: AsyncEngine, redis: Redis, timeout_seconds: float) -> None:
        self._engine = engine
        self._redis = redis
        self._timeout_seconds = timeout_seconds

    async def _check_postgres(self) -> DependencyStatus:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                async with self._engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            return DependencyStatus(status="up")
        except Exception as exc:
            return DependencyStatus(status="down", detail=type(exc).__name__)

    async def _check_redis(self) -> DependencyStatus:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await self._redis.ping()
            return DependencyStatus(status="up")
        except Exception as exc:
            return DependencyStatus(status="down", detail=type(exc).__name__)

    async def check(self) -> dict[str, DependencyStatus]:
        postgres, redis = await asyncio.gather(self._check_postgres(), self._check_redis())
        return {"postgres": postgres, "redis": redis}
