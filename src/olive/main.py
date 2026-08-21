from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from olive.api.health import router as health_router
from olive.cache import create_redis_client
from olive.config import get_settings
from olive.db import create_database_engine
from olive.health import InfrastructureHealthChecker
from olive.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(settings.database_url)
        redis = create_redis_client(settings.redis_url)
        app.state.health_checker = InfrastructureHealthChecker(
            engine=engine,
            redis=redis,
            timeout_seconds=settings.dependency_timeout_seconds,
        )
        logger.info("application_started", extra={"environment": settings.app_env.value})
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()
            logger.info("application_stopped")

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    return application


app = create_app()

