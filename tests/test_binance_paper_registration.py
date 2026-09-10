from olive.smoke.binance_paper import BINANCE_PERPETUALS


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
