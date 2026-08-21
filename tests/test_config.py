from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from olive.config import AppEnvironment, Settings


def test_environment_names_are_explicit() -> None:
    assert {environment.value for environment in AppEnvironment} == {
        "development",
        "testing",
        "paper",
        "staging",
        "production",
    }


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="live")  # type: ignore[arg-type]


def test_dependency_timeout_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(dependency_timeout_seconds=0)


def test_signal_secret_is_redacted_from_settings_representation() -> None:
    settings = Settings(signal_hmac_secret=SecretStr("never-print-this"))
    assert "never-print-this" not in repr(settings)


def test_nonce_ttl_must_cover_freshness_window() -> None:
    with pytest.raises(ValidationError):
        Settings(signal_max_age_seconds=600, signal_nonce_ttl_seconds=300)
