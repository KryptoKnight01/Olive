from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from olive.config import AppEnvironment, Settings, get_settings
from olive.db import get_session
from olive.gateway.auth import GatewayHeaders, SignalAuthenticator
from olive.gateway.errors import (
    GatewayAuthenticationError,
    GatewayUnavailableError,
    SignalIntakeError,
)
from olive.gateway.schemas import SignalIntakeResponse
from olive.gateway.service import SignalIntakeService
from olive.paper.orchestration import AutomaticPaperOrchestrator

router = APIRouter(prefix="/api/v1/signals", tags=["signal-gateway"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_signal_authenticator(request: Request) -> SignalAuthenticator:
    return cast(SignalAuthenticator, request.app.state.signal_authenticator)


AuthenticatorDependency = Annotated[SignalAuthenticator, Depends(get_signal_authenticator)]


async def ingest_and_maybe_execute(
    body: bytes, session: AsyncSession, settings: Settings
) -> SignalIntakeResponse:
    response = await SignalIntakeService(session, settings).ingest(body)
    if settings.paper_auto_execute:
        paper_execution = await AutomaticPaperOrchestrator(session, settings).execute(
            response.intake_id
        )
        return response.model_copy(update={"paper_execution": paper_execution})
    return response


@router.post(
    "/tradingview",
    response_model=SignalIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_tradingview_signal(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    authenticator: AuthenticatorDependency,
    key_id: Annotated[str, Header(alias="X-Olive-Key-Id")],
    timestamp: Annotated[str, Header(alias="X-Olive-Timestamp")],
    nonce: Annotated[str, Header(alias="X-Olive-Nonce")],
    signature: Annotated[str, Header(alias="X-Olive-Signature")],
) -> SignalIntakeResponse:
    body = await request.body()
    if len(body) > settings.signal_max_payload_bytes:
        raise SignalIntakeError("signal payload is too large", code="PAYLOAD_TOO_LARGE")
    await authenticator.authenticate(
        body,
        GatewayHeaders(
            key_id=key_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        ),
    )
    return await ingest_and_maybe_execute(body, session, settings)


@router.post(
    "/tradingview-alert",
    response_model=SignalIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_tradingview_alert(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    authenticator: AuthenticatorDependency,
) -> SignalIntakeResponse:
    """Accept a TradingView-compatible body secret in paper/staging only."""
    if settings.app_env not in {AppEnvironment.PAPER, AppEnvironment.STAGING}:
        raise GatewayUnavailableError("TradingView alert bridge is limited to paper and staging")
    configured = settings.tradingview_webhook_secret
    configured_value = configured.get_secret_value() if configured is not None else ""
    if len(configured_value) < 32:
        raise GatewayUnavailableError("TradingView alert bridge is not configured")
    raw_body = await request.body()
    if len(raw_body) > settings.signal_max_payload_bytes:
        raise SignalIntakeError("signal payload is too large", code="PAYLOAD_TOO_LARGE")
    try:
        payload = json.loads(raw_body)
        supplied = payload.pop("webhook_secret")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GatewayAuthenticationError("invalid TradingView alert credentials") from exc
    if not isinstance(supplied, str) or not hmac.compare_digest(
        supplied, configured_value
    ):
        raise GatewayAuthenticationError("invalid TradingView alert credentials")

    external_signal_id = str(payload.get("signal_id", "")).strip()
    try:
        payload["signal_id"] = str(uuid.UUID(external_signal_id))
    except ValueError as exc:
        if not external_signal_id:
            raise SignalIntakeError(
                "signal_id is required", code="INVALID_PAYLOAD"
            ) from exc
        payload["signal_id"] = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"olive:tradingview:{external_signal_id}")
        )
    if "expiry" not in payload:
        try:
            timestamp_value = datetime.fromisoformat(
                str(payload["timestamp"]).replace("Z", "+00:00")
            ).astimezone(UTC)
            expiry_seconds = int(payload.pop("expiry_seconds", 300))
        except (KeyError, TypeError, ValueError) as exc:
            raise SignalIntakeError("valid timestamp is required", code="INVALID_PAYLOAD") from exc
        payload["expiry"] = (timestamp_value + timedelta(seconds=expiry_seconds)).isoformat()

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp = str(int(time.time()))
    nonce = f"tradingview-{uuid.uuid4()}"
    signal_secret = settings.signal_hmac_secret
    if signal_secret is None or not signal_secret.get_secret_value():
        raise GatewayUnavailableError("signal authentication is not configured")
    message = timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body
    signature = hmac.new(
        signal_secret.get_secret_value().encode(), message, hashlib.sha256
    ).hexdigest()
    await authenticator.authenticate(
        body,
        GatewayHeaders(
            key_id=settings.signal_hmac_key_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=f"sha256={signature}",
        ),
    )
    return await ingest_and_maybe_execute(body, session, settings)
