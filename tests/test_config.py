from __future__ import annotations

import pytest
from pydantic import ValidationError

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
