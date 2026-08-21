from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, NoReturn, cast

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from olive.config import Settings
from olive.domain.models import (
    Instrument,
    RecordStatus,
    Strategy,
    StrategyVersion,
    Underlying,
    Venue,
    VenueInstrument,
)
from olive.gateway.errors import DuplicateSignalError, SignalIntakeError
from olive.gateway.models import SignalIntakeRecord, SignalIntakeStatus
from olive.gateway.schemas import SignalIntakeResponse, SignalPayload


class SignalIntakeService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session = session
        self._settings = settings
        self._clock = clock

    async def ingest(self, body: bytes) -> SignalIntakeResponse:
        payload_hash = hashlib.sha256(body).hexdigest()
        try:
            raw = self._decode_json(body)
        except SignalIntakeError as exc:
            record = SignalIntakeRecord(
                status=SignalIntakeStatus.REJECTED,
                rejection_code=exc.code,
                rejection_reason=str(exc),
                payload_hash=payload_hash,
                raw_payload=None,
            )
            await self._persist(record)
            raise SignalIntakeError(str(exc), code=exc.code, intake_id=record.id) from exc
        try:
            payload = SignalPayload.model_validate(raw)
        except ValidationError as exc:
            record = await self._reject(
                raw=raw,
                payload_hash=payload_hash,
                code="SCHEMA_INVALID",
                reason=self._schema_reason(exc),
                signal_id=self._extract_signal_id(raw),
            )
            raise SignalIntakeError(
                "signal payload failed schema validation",
                code="SCHEMA_INVALID",
                intake_id=record.id,
            ) from exc

        duplicate = await self._session.scalar(
            select(SignalIntakeRecord).where(SignalIntakeRecord.signal_id == payload.signal_id)
        )
        if duplicate is not None:
            raise DuplicateSignalError("signal ID has already been received")

        now = self._clock().astimezone(UTC)
        if abs((now - payload.timestamp).total_seconds()) > self._settings.signal_max_age_seconds:
            await self._reject_payload(
                payload, raw, payload_hash, "STALE_SIGNAL", "signal is stale"
            )
        if payload.expiry <= now:
            await self._reject_payload(
                payload, raw, payload_hash, "EXPIRED_SIGNAL", "signal has expired"
            )
        if payload.environment.value != self._settings.app_env.value:
            await self._reject_payload(
                payload,
                raw,
                payload_hash,
                "ENVIRONMENT_MISMATCH",
                "signal environment does not match the receiving service",
            )

        strategy_version = await self._resolve_strategy_version(payload)
        if strategy_version is None:
            await self._reject_payload(
                payload,
                raw,
                payload_hash,
                "UNKNOWN_STRATEGY_VERSION",
                "strategy version or configuration version is unknown",
            )
        mapping = await self._resolve_mapping(payload)
        if mapping is None:
            await self._reject_payload(
                payload,
                raw,
                payload_hash,
                "UNKNOWN_INSTRUMENT",
                "venue instrument mapping is unknown or inactive",
            )

        record = self._record_from_payload(
            payload,
            raw,
            payload_hash,
            status=SignalIntakeStatus.RECEIVED,
            strategy_version_id=strategy_version.id,
            venue_instrument_id=mapping.id,
        )
        await self._persist(record)
        return SignalIntakeResponse(
            intake_id=record.id,
            signal_id=payload.signal_id,
            status=record.status,
        )

    def _decode_json(self, body: bytes) -> dict[str, Any]:
        try:
            value = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SignalIntakeError(
                "request body must be a valid JSON object", code="MALFORMED_JSON"
            ) from exc
        if not isinstance(value, dict):
            raise SignalIntakeError("request body must be a JSON object", code="MALFORMED_JSON")
        return value

    async def _resolve_strategy_version(self, payload: SignalPayload) -> StrategyVersion | None:
        return cast(
            StrategyVersion | None,
            await self._session.scalar(
                select(StrategyVersion)
                .join(Strategy, Strategy.id == StrategyVersion.strategy_id)
                .where(
                    Strategy.code == payload.strategy_id,
                    StrategyVersion.version == payload.strategy_version,
                    StrategyVersion.configuration_version == payload.configuration_version,
                )
            ),
        )

    async def _resolve_mapping(self, payload: SignalPayload) -> VenueInstrument | None:
        return cast(
            VenueInstrument | None,
            await self._session.scalar(
                select(VenueInstrument)
                .join(Venue, Venue.id == VenueInstrument.venue_id)
                .join(Instrument, Instrument.id == VenueInstrument.instrument_id)
                .join(Underlying, Underlying.id == Instrument.underlying_id)
                .where(
                    Venue.code == payload.venue,
                    VenueInstrument.symbol == payload.instrument,
                    VenueInstrument.status == RecordStatus.ACTIVE,
                    Instrument.status == RecordStatus.ACTIVE,
                    Underlying.status == RecordStatus.ACTIVE,
                )
            ),
        )

    async def _reject_payload(
        self,
        payload: SignalPayload,
        raw: dict[str, Any],
        payload_hash: str,
        code: str,
        reason: str,
    ) -> NoReturn:
        record = self._record_from_payload(
            payload,
            raw,
            payload_hash,
            status=SignalIntakeStatus.REJECTED,
            rejection_code=code,
            rejection_reason=reason,
        )
        await self._persist(record)
        raise SignalIntakeError(reason, code=code, intake_id=record.id)

    async def _reject(
        self,
        *,
        raw: dict[str, Any],
        payload_hash: str,
        code: str,
        reason: str,
        signal_id: uuid.UUID | None,
    ) -> SignalIntakeRecord:
        record = SignalIntakeRecord(
            signal_id=signal_id,
            status=SignalIntakeStatus.REJECTED,
            rejection_code=code,
            rejection_reason=reason,
            payload_hash=payload_hash,
            raw_payload=raw,
        )
        await self._persist(record)
        return record

    def _record_from_payload(
        self,
        payload: SignalPayload,
        raw: dict[str, Any],
        payload_hash: str,
        *,
        status: SignalIntakeStatus,
        rejection_code: str | None = None,
        rejection_reason: str | None = None,
        strategy_version_id: uuid.UUID | None = None,
        venue_instrument_id: uuid.UUID | None = None,
    ) -> SignalIntakeRecord:
        return SignalIntakeRecord(
            signal_id=payload.signal_id,
            status=status,
            rejection_code=rejection_code,
            rejection_reason=rejection_reason,
            payload_hash=payload_hash,
            raw_payload=raw,
            strategy_version_id=strategy_version_id,
            venue_instrument_id=venue_instrument_id,
            configuration_version=payload.configuration_version,
            environment=payload.environment,
            emitted_at=payload.timestamp,
            expires_at=payload.expiry,
            direction=payload.direction,
            entry_price=payload.entry_price,
            reference_price=payload.reference_price,
            stop_price=payload.stop,
            targets=[str(value) for value in payload.targets],
            expected_rr=payload.expected_rr,
            timeframe=payload.timeframe,
            setup_score=payload.setup_score,
            regime=payload.regime,
        )

    async def _persist(self, record: SignalIntakeRecord) -> None:
        self._session.add(record)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateSignalError("signal ID has already been received") from exc

    @staticmethod
    def _extract_signal_id(raw: dict[str, Any]) -> uuid.UUID | None:
        try:
            return uuid.UUID(str(raw.get("signal_id")))
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _schema_reason(exc: ValidationError) -> str:
        first = exc.errors(include_url=False, include_input=False)[0]
        location = ".".join(str(part) for part in first["loc"])
        return f"invalid field {location}: {first['msg']}"[:500]
