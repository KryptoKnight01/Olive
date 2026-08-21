from __future__ import annotations

import asyncio
import hashlib
import hmac

import pytest
from pydantic import SecretStr
from redis.exceptions import ConnectionError

from olive.config import Settings
from olive.gateway.auth import GatewayHeaders, SignalAuthenticator
from olive.gateway.errors import (
    GatewayAuthenticationError,
    GatewayRateLimitError,
    GatewayReplayError,
    GatewayUnavailableError,
)


class FakeRedis:
    def __init__(self) -> None:
        self.count = 0
        self.nonces: set[str] = set()
        self.fail = False

    async def eval(self, _script: str, _keys: int, _key: str, _window: int) -> int:
        if self.fail:
            raise ConnectionError("unavailable")
        self.count += 1
        return self.count

    async def set(self, key: str, _value: str, **_kwargs: object) -> bool:
        if self.fail:
            raise ConnectionError("unavailable")
        if key in self.nonces:
            return False
        self.nonces.add(key)
        return True


def auth_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "signal_hmac_key_id": "tradingview-test",
        "signal_hmac_secret": SecretStr("test-secret"),
        "signal_max_age_seconds": 300,
        "signal_nonce_ttl_seconds": 900,
        "signal_rate_limit": 2,
        "signal_rate_window_seconds": 60,
    }
    values.update(overrides)
    return Settings(**values)


def signed_headers(body: bytes, timestamp: int, nonce: str = "nonce-1") -> GatewayHeaders:
    message = str(timestamp).encode() + b"\n" + nonce.encode() + b"\n" + body
    signature = hmac.new(b"test-secret", message, hashlib.sha256).hexdigest()
    return GatewayHeaders(
        key_id="tradingview-test",
        timestamp=str(timestamp),
        nonce=nonce,
        signature=f"sha256={signature}",
    )


async def test_valid_signature_reserves_nonce() -> None:
    redis = FakeRedis()
    authenticator = SignalAuthenticator(redis, auth_settings(), clock=lambda: 1_000)  # type: ignore[arg-type]
    await authenticator.authenticate(b'{"ok":true}', signed_headers(b'{"ok":true}', 1_000))
    assert len(redis.nonces) == 1


async def test_invalid_signature_is_rejected_before_redis() -> None:
    redis = FakeRedis()
    authenticator = SignalAuthenticator(redis, auth_settings(), clock=lambda: 1_000)  # type: ignore[arg-type]
    headers = signed_headers(b"original", 1_000)
    with pytest.raises(GatewayAuthenticationError):
        await authenticator.authenticate(b"tampered", headers)
    assert redis.count == 0


async def test_stale_webhook_is_rejected() -> None:
    authenticator = SignalAuthenticator(FakeRedis(), auth_settings(), clock=lambda: 2_000)  # type: ignore[arg-type]
    with pytest.raises(GatewayAuthenticationError, match="freshness"):
        await authenticator.authenticate(b"{}", signed_headers(b"{}", 1_000))


async def test_reused_nonce_is_rejected() -> None:
    authenticator = SignalAuthenticator(FakeRedis(), auth_settings(), clock=lambda: 1_000)  # type: ignore[arg-type]
    headers = signed_headers(b"{}", 1_000)
    await authenticator.authenticate(b"{}", headers)
    with pytest.raises(GatewayReplayError):
        await authenticator.authenticate(b"{}", headers)


async def test_rate_limit_is_enforced() -> None:
    authenticator = SignalAuthenticator(FakeRedis(), auth_settings(), clock=lambda: 1_000)  # type: ignore[arg-type]
    await authenticator.authenticate(b"{}", signed_headers(b"{}", 1_000, "n1"))
    await authenticator.authenticate(b"{}", signed_headers(b"{}", 1_000, "n2"))
    with pytest.raises(GatewayRateLimitError):
        await authenticator.authenticate(b"{}", signed_headers(b"{}", 1_000, "n3"))


async def test_redis_failure_fails_closed() -> None:
    redis = FakeRedis()
    redis.fail = True
    authenticator = SignalAuthenticator(redis, auth_settings(), clock=lambda: 1_000)  # type: ignore[arg-type]
    with pytest.raises(GatewayUnavailableError):
        await authenticator.authenticate(b"{}", signed_headers(b"{}", 1_000))


async def test_concurrent_reuse_allows_exactly_one_nonce() -> None:
    authenticator = SignalAuthenticator(FakeRedis(), auth_settings(), clock=lambda: 1_000)  # type: ignore[arg-type]
    headers = signed_headers(b"{}", 1_000, "same-nonce")
    outcomes = await asyncio.gather(
        authenticator.authenticate(b"{}", headers),
        authenticator.authenticate(b"{}", headers),
        return_exceptions=True,
    )
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, GatewayReplayError) for outcome in outcomes) == 1
