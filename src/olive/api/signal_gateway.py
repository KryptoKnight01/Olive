from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from olive.config import Settings, get_settings
from olive.db import get_session
from olive.gateway.auth import GatewayHeaders, SignalAuthenticator
from olive.gateway.errors import SignalIntakeError
from olive.gateway.schemas import SignalIntakeResponse
from olive.gateway.service import SignalIntakeService

router = APIRouter(prefix="/api/v1/signals", tags=["signal-gateway"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_signal_authenticator(request: Request) -> SignalAuthenticator:
    return cast(SignalAuthenticator, request.app.state.signal_authenticator)


AuthenticatorDependency = Annotated[SignalAuthenticator, Depends(get_signal_authenticator)]


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
    return await SignalIntakeService(session, settings).ingest(body)
