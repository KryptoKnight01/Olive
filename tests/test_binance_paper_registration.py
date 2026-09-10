import pytest

from olive.smoke.binance_paper import BINANCE_PERPETUALS, resolve_symbols


def test_binance_paper_universe_uses_venue_symbols_and_canonical_codes() -> None:
    assert {item.venue_symbol for item in BINANCE_PERPETUALS} == {
        "BTCUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT",
    }
    assert {item.instrument_code for item in BINANCE_PERPETUALS} == {
        "BTC-USDT-PERP",
        "BNB-USDT-PERP",
        "SOL-USDT-PERP",
        "XRP-USDT-PERP",
    }


def test_additional_binance_symbol_is_derived_generically() -> None:
    definition = resolve_symbols(["adausdt"])[0]
    assert definition.venue_symbol == "ADAUSDT"
    assert definition.instrument_code == "ADA-USDT-PERP"


def test_non_usdt_symbol_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported Binance USDT perpetual symbol"):
        resolve_symbols(["BTCUSD"])
