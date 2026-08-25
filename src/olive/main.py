from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from olive.api.health import router as health_router
from olive.cache import create_redis_client
from olive.config import get_settings
from olive.db import create_database_engine, create_session_factory
from olive.domain.errors import DomainConflict, DomainNotFound, DomainValidationError
from olive.gateway.auth import SignalAuthenticator
from olive.gateway.errors import GatewayError
from olive.health import InfrastructureHealthChecker
from olive.logging import configure_logging
from olive.market_data.service import MarketDataError


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(settings.database_url)
        app.state.session_factory = create_session_factory(engine)
        redis = create_redis_client(settings.redis_url)
        app.state.signal_authenticator = SignalAuthenticator(redis=redis, settings=settings)
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
    from olive.api.asset_master import router as asset_master_router
    from olive.api.market_data import router as market_data_router
    from olive.api.signal_gateway import router as signal_gateway_router

    application.include_router(asset_master_router)
    application.include_router(market_data_router)
    application.include_router(signal_gateway_router)

    @application.exception_handler(DomainNotFound)
    async def handle_not_found(_request: object, exc: DomainNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"code": exc.code, "detail": str(exc)})

    @application.exception_handler(DomainConflict)
    async def handle_conflict(_request: object, exc: DomainConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"code": exc.code, "detail": str(exc)})

    @application.exception_handler(DomainValidationError)
    async def handle_validation(_request: object, exc: DomainValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"code": exc.code, "detail": str(exc)})

    @application.exception_handler(GatewayError)
    async def handle_gateway_error(_request: object, exc: GatewayError) -> JSONResponse:
        content: dict[str, object] = {"code": exc.code, "detail": str(exc)}
        intake_id = getattr(exc, "intake_id", None)
        if intake_id is not None:
            content["intake_id"] = str(intake_id)
        return JSONResponse(status_code=exc.status_code, content=content)

    @application.exception_handler(MarketDataError)
    async def handle_market_data_error(_request: object, exc: MarketDataError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "MARKET_DATA_ERROR", "detail": str(exc)},
        )

    return application


app = create_app()
