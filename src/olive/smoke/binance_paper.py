from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from olive.config import get_settings
from olive.db import create_database_engine, create_session_factory
from olive.domain.models import (
    Asset,
    AssetClass,
    Instrument,
    InstrumentType,
    Underlying,
    Venue,
    VenueInstrument,
)


@dataclass(frozen=True)
class BinancePerpetual:
    asset_code: str
    asset_name: str
    venue_symbol: str
    tick_size: str
    lot_size: str

    @property
    def instrument_code(self) -> str:
        return f"{self.asset_code}-USDT-PERP"


BINANCE_PERPETUALS = (
    BinancePerpetual("BTC", "Bitcoin", "BTCUSDT", "0.10", "0.001"),
    BinancePerpetual("BNB", "BNB", "BNBUSDT", "0.01", "0.01"),
    BinancePerpetual("SOL", "Solana", "SOLUSDT", "0.001", "0.1"),
    BinancePerpetual("XRP", "XRP", "XRPUSDT", "0.0001", "1"),
)


def resolve_symbols(symbols: list[str] | None) -> tuple[BinancePerpetual, ...]:
    if not symbols:
        return BINANCE_PERPETUALS
    catalog = {item.venue_symbol: item for item in BINANCE_PERPETUALS}
    resolved: list[BinancePerpetual] = []
    for raw_symbol in symbols:
        symbol = raw_symbol.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{2,16}USDT", symbol):
            raise ValueError(f"unsupported Binance USDT perpetual symbol: {raw_symbol}")
        definition = catalog.get(symbol)
        if definition is None:
            asset_code = symbol.removesuffix("USDT")
            definition = BinancePerpetual(
                asset_code, asset_code, symbol, "0.00000001", "0.00000001"
            )
        if definition not in resolved:
            resolved.append(definition)
    return tuple(resolved)


async def ensure_asset(session: AsyncSession, code: str, name: str) -> Asset:
    asset = await session.scalar(select(Asset).where(Asset.code == code))
    if asset is None:
        asset = Asset(code=code, name=name, asset_class=AssetClass.CRYPTO)
        session.add(asset)
        await session.flush()
    return asset


async def ensure_underlying(
    session: AsyncSession, asset: Asset, definition: BinancePerpetual
) -> Underlying:
    underlying = await session.scalar(
        select(Underlying).where(Underlying.code == definition.asset_code)
    )
    if underlying is None:
        underlying = Underlying(
            code=definition.asset_code,
            name=f"{definition.asset_name} economic exposure",
            primary_asset_id=asset.id,
            asset_class=AssetClass.CRYPTO,
            themes=["crypto-beta"],
        )
        session.add(underlying)
        await session.flush()
    return underlying


async def register(symbols: list[str] | None = None) -> None:
    definitions = resolve_symbols(symbols)
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            usdt = await session.scalar(select(Asset).where(Asset.code == "USDT"))
            if usdt is None:
                usdt = Asset(
                    code="USDT",
                    name="Tether USD",
                    asset_class=AssetClass.CASH,
                    currency_code="USD",
                )
                session.add(usdt)
                await session.flush()

            venue = await session.scalar(select(Venue).where(Venue.code == "BINANCE"))
            if venue is None:
                venue = Venue(code="BINANCE", name="Binance", timezone="UTC")
                session.add(venue)
                await session.flush()

            for definition in definitions:
                asset = await ensure_asset(
                    session, definition.asset_code, definition.asset_name
                )
                underlying = await ensure_underlying(session, asset, definition)
                instrument = await session.scalar(
                    select(Instrument).where(
                        Instrument.code == definition.instrument_code
                    )
                )
                if instrument is None:
                    instrument = Instrument(
                        code=definition.instrument_code,
                        name=f"{definition.asset_name} / Tether USD Perpetual",
                        underlying_id=underlying.id,
                        base_asset_id=asset.id,
                        quote_asset_id=usdt.id,
                        settlement_asset_id=usdt.id,
                        instrument_type=InstrumentType.PERPETUAL,
                        tick_size=Decimal(definition.tick_size),
                        lot_size=Decimal(definition.lot_size),
                        contract_multiplier=Decimal("1"),
                        max_leverage=Decimal("125"),
                        shortable=True,
                        session_name="24x7",
                    )
                    session.add(instrument)
                    await session.flush()

                mapping = await session.scalar(
                    select(VenueInstrument).where(
                        VenueInstrument.venue_id == venue.id,
                        VenueInstrument.symbol == definition.venue_symbol,
                    )
                )
                if mapping is None:
                    session.add(
                        VenueInstrument(
                            venue_id=venue.id,
                            instrument_id=instrument.id,
                            symbol=definition.venue_symbol,
                        )
                    )

            await session.commit()
    finally:
        await engine.dispose()

    registered = ", ".join(item.venue_symbol for item in definitions)
    print(f"PASS Binance perpetuals registered for paper analysis: {registered}")
    print("Live trading remains disarmed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="*")
    args = parser.parse_args()
    asyncio.run(register(args.symbols))
