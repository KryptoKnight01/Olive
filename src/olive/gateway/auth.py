from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from olive.config import Settings
from olive.gateway.errors import (
    GatewayAuthenticationError,
    GatewayRateLimitError,
    GatewayReplayError,
    GatewayUnavailableError,
)

RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


@dataclass(frozen=True)
class GatewayHeaders:
    key_id: str
    timestamp: str
    nonce: str
    signature: str


class SignalAuthenticator:
    def __init__(
        self,
        redis: Redis,
        settings: Settings,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis = redis
        self._settings = settings
        self._clock = clock

    async def authenticate(self, body: bytes, headers: GatewayHeaders) -> None:
        secret = self._settings.signal_hmac_secret
        if secret is None or not secret.get_secret_value():
            raise GatewayUnavailableError("signal authentication is not configured")
        if not hmac.compare_digest(headers.key_id, self._settings.signal_hmac_key_id):
            raise GatewayAuthenticationError("invalid webhook credentials")
        try:
            timestamp = int(headers.timestamp)
        except ValueError as exc:
            raise GatewayAuthenticationError("invalid webhook timestamp") from exc
        age = abs(int(self._clock()) - timestamp)
        if age > self._settings.signal_max_age_seconds:
            raise GatewayAuthenticationError(
                "webhook timestamp is outside the accepted freshness window",
                code="STALE_WEBHOOK",
            )
        nonce = headers.nonce.strip()
        if not nonce or len(nonce) > 128:
            raise GatewayAuthenticationError("invalid webhook nonce")

        signed_message = headers.timestamp.encode() + b"\n" + nonce.encode() + b"\n" + body
        expected = hmac.new(
            secret.get_secret_value().encode(), signed_message, hashlib.sha256
        ).hexdigest()
        supplied = headers.signature.removeprefix("sha256=").lower()
        if len(supplied) != 64 or not hmac.compare_digest(supplied, expected):
            raise GatewayAuthenticationError("invalid webhook signature")

        try:
            rate_key = f"olive:gateway:rate:{headers.key_id}"
            raw_count = await cast(
                Awaitable[object],
                self._redis.eval(
                    RATE_LIMIT_SCRIPT,
                    1,
                    rate_key,
                    str(self._settings.signal_rate_window_seconds),
                ),
            )
            count = int(cast(int | str, raw_count))
            if count > self._settings.signal_rate_limit:
                raise GatewayRateLimitError("webhook rate limit exceeded")

            nonce_key = f"olive:gateway:nonce:{headers.key_id}:{nonce}"
            reserved = await cast(
                Awaitable[object],
                self._redis.set(
                    nonce_key,
                    "1",
                    ex=self._settings.signal_nonce_ttl_seconds,
                    nx=True,
                ),
            )
            if not reserved:
                raise GatewayReplayError("webhook nonce has already been used")
        except RedisError as exc:
            raise GatewayUnavailableError("replay protection is unavailable") from exc
