from __future__ import annotations

import asyncio
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


async def register() -> None:
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

            for definition in BINANCE_PERPETUALS:
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

    symbols = ", ".join(item.venue_symbol for item in BINANCE_PERPETUALS)
    print(f"PASS Binance perpetuals registered for paper analysis: {symbols}")
    print("Live trading remains disarmed")


if __name__ == "__main__":
    asyncio.run(register())
