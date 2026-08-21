from __future__ import annotations

from sqlalchemy import Numeric

from olive.db import Base
from olive.domain.models import Instrument


def test_phase_1_tables_are_registered() -> None:
    assert {
        "assets",
        "underlyings",
        "instruments",
        "venues",
        "venue_instruments",
        "accounts",
        "portfolios",
        "strategies",
        "strategy_versions",
    }.issubset(Base.metadata.tables)


def test_critical_instrument_values_use_fixed_precision() -> None:
    for name in ("tick_size", "lot_size", "contract_multiplier", "max_leverage"):
        assert isinstance(Instrument.__table__.columns[name].type, Numeric)
