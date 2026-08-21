from __future__ import annotations

import uuid


class GatewayError(Exception):
    code = "GATEWAY_ERROR"
    status_code = 400

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class GatewayAuthenticationError(GatewayError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401


class GatewayReplayError(GatewayError):
    code = "REPLAY_DETECTED"
    status_code = 409


class GatewayRateLimitError(GatewayError):
    code = "RATE_LIMITED"
    status_code = 429


class GatewayUnavailableError(GatewayError):
    code = "GATEWAY_UNAVAILABLE"
    status_code = 503


class SignalIntakeError(GatewayError):
    code = "SIGNAL_REJECTED"
    status_code = 422

    def __init__(
        self, message: str, *, code: str | None = None, intake_id: uuid.UUID | None = None
    ) -> None:
        super().__init__(message, code=code)
        self.intake_id = intake_id


class DuplicateSignalError(GatewayError):
    code = "DUPLICATE_SIGNAL"
    status_code = 409
