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


def test_admin_secret_is_redacted_and_requires_minimum_length() -> None:
    with pytest.raises(ValidationError):
        Settings(admin_api_key=SecretStr("short"))
    settings = Settings(admin_api_key=SecretStr("a" * 32))
    assert "a" * 32 not in repr(settings)


def test_nonce_ttl_must_cover_freshness_window() -> None:
    with pytest.raises(ValidationError):
        Settings(signal_max_age_seconds=600, signal_nonce_ttl_seconds=300)


def test_automatic_paper_execution_is_restricted_to_safe_environments() -> None:
    with pytest.raises(ValidationError, match="paper or staging"):
        Settings(app_env=AppEnvironment.PRODUCTION, paper_auto_execute=True)
    assert Settings(
        app_env=AppEnvironment.STAGING, paper_auto_execute=True
    ).paper_auto_execute
