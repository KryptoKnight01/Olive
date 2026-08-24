from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from olive.domain.models import RecordStatus, StrategyState, StrategyVersion, VenueInstrument
from olive.gateway.models import SignalDirection, SignalEnvironment
from olive.gateway.schemas import SignalPayload
from olive.validation.models import SignalValidationPolicy


@dataclass(frozen=True)
class ValidationFailure:
    code: str
    reason: str
    details: dict[str, object]


class SignalValidationEngine:
    def validate(
        self,
        payload: SignalPayload,
        strategy_version: StrategyVersion,
        mapping: VenueInstrument,
        policy: SignalValidationPolicy | None,
    ) -> ValidationFailure | None:
        if policy is None:
            return self._failure(
                "VALIDATION_POLICY_MISSING", "strategy validation policy is not configured"
            )
        if not policy.enabled:
            return self._failure("STRATEGY_DISABLED", "strategy validation policy is disabled")
        if strategy_version.strategy.status is not RecordStatus.ACTIVE:
            return self._failure("STRATEGY_DISABLED", "strategy is not active")
        if strategy_version.state is not self._required_state(payload.environment):
            return self._failure(
                "STRATEGY_VERSION_DISABLED",
                "strategy version is not enabled for the signal environment",
                required_state=self._required_state(payload.environment).value,
                actual_state=strategy_version.state.value,
            )

        entity_statuses = (
            ("venue", mapping.venue.status),
            ("venue instrument", mapping.status),
            ("instrument", mapping.instrument.status),
            ("underlying", mapping.instrument.underlying.status),
            ("base asset", mapping.instrument.base_asset.status),
            ("quote asset", mapping.instrument.quote_asset.status),
            ("settlement asset", mapping.instrument.settlement_asset.status),
        )
        for label, entity_status in entity_statuses:
            if entity_status is not RecordStatus.ACTIVE:
                return self._failure("INSTRUMENT_DISABLED", f"{label} is not active", entity=label)

        if payload.direction.value not in policy.allowed_directions:
            return self._failure(
                "DIRECTION_NOT_ALLOWED",
                "signal direction is not allowed",
                direction=payload.direction.value,
            )
        if policy.allowed_timeframes and payload.timeframe not in policy.allowed_timeframes:
            return self._failure(
                "TIMEFRAME_NOT_ALLOWED",
                "signal timeframe is not allowed",
                timeframe=payload.timeframe,
            )

        deviation_pct = abs(payload.entry_price - payload.reference_price) / payload.reference_price
        deviation_pct *= Decimal("100")
        if deviation_pct > policy.max_entry_deviation_pct:
            return self._failure(
                "ENTRY_DEVIATION_EXCEEDED",
                "entry price deviation exceeds the configured maximum",
                actual_pct=str(deviation_pct),
                maximum_pct=str(policy.max_entry_deviation_pct),
            )

        if payload.direction is SignalDirection.LONG:
            logical_prices = payload.stop < payload.entry_price and all(
                target > payload.entry_price for target in payload.targets
            )
        else:
            logical_prices = payload.stop > payload.entry_price and all(
                target < payload.entry_price for target in payload.targets
            )
        if not logical_prices:
            return self._failure(
                "INVALID_STOP_TARGET_LOGIC",
                "stop and targets are not logical for the signal direction",
            )
        if payload.expected_rr < policy.min_expected_rr:
            return self._failure(
                "MINIMUM_RR_NOT_MET",
                "expected risk/reward is below the configured minimum",
                actual=str(payload.expected_rr),
                minimum=str(policy.min_expected_rr),
            )
        if payload.setup_score < policy.min_setup_score:
            return self._failure(
                "MINIMUM_SETUP_SCORE_NOT_MET",
                "setup score is below the configured minimum",
                actual=str(payload.setup_score),
                minimum=str(policy.min_setup_score),
            )

        session_failure = self._validate_session(payload, policy)
        if session_failure is not None:
            return session_failure
        return None

    def _validate_session(
        self, payload: SignalPayload, policy: SignalValidationPolicy
    ) -> ValidationFailure | None:
        try:
            local_timestamp = payload.timestamp.astimezone(ZoneInfo(policy.session_timezone))
        except ZoneInfoNotFoundError:
            return self._failure("VALIDATION_CONFIGURATION_INVALID", "session timezone is invalid")
        if local_timestamp.weekday() not in policy.allowed_weekdays:
            return self._failure("SESSION_CLOSED", "signal was emitted on a disabled weekday")
        if policy.session_start is None and policy.session_end is None:
            return None
        if policy.session_start is None or policy.session_end is None:
            return self._failure(
                "VALIDATION_CONFIGURATION_INVALID",
                "session start and end must both be configured",
            )
        try:
            start = time.fromisoformat(policy.session_start)
            end = time.fromisoformat(policy.session_end)
        except ValueError:
            return self._failure("VALIDATION_CONFIGURATION_INVALID", "session time is invalid")
        current = local_timestamp.timetz().replace(tzinfo=None)
        in_session = start <= current < end if start < end else current >= start or current < end
        if not in_session:
            return self._failure("SESSION_CLOSED", "signal was emitted outside the session")
        return None

    @staticmethod
    def _required_state(environment: SignalEnvironment) -> StrategyState:
        return {
            SignalEnvironment.DEVELOPMENT: StrategyState.DEVELOPMENT,
            SignalEnvironment.TESTING: StrategyState.DEVELOPMENT,
            SignalEnvironment.PAPER: StrategyState.PAPER,
            SignalEnvironment.STAGING: StrategyState.STAGING,
            SignalEnvironment.PRODUCTION: StrategyState.LIVE,
        }[environment]

    @staticmethod
    def _failure(code: str, reason: str, **details: object) -> ValidationFailure:
        return ValidationFailure(code=code, reason=reason, details=details)
