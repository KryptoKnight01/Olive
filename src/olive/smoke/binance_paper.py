from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

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


async def register() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            btc = await session.scalar(select(Asset).where(Asset.code == "BTC"))
            underlying = await session.scalar(
                select(Underlying).where(Underlying.code == "BTC")
            )
            if btc is None or underlying is None:
                raise RuntimeError("BTC reference data is missing; run the staging seed first")

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

            instrument = await session.scalar(
                select(Instrument).where(Instrument.code == "BTC-USDT-PERP")
            )
            if instrument is None:
                instrument = Instrument(
                    code="BTC-USDT-PERP",
                    name="Bitcoin / Tether USD Perpetual",
                    underlying_id=underlying.id,
                    base_asset_id=btc.id,
                    quote_asset_id=usdt.id,
                    settlement_asset_id=usdt.id,
                    instrument_type=InstrumentType.PERPETUAL,
                    tick_size=Decimal("0.10"),
                    lot_size=Decimal("0.001"),
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
                    VenueInstrument.symbol == "BTCUSDT",
                )
            )
            if mapping is None:
                session.add(
                    VenueInstrument(
                        venue_id=venue.id,
                        instrument_id=instrument.id,
                        symbol="BTCUSDT",
                    )
                )

            await session.commit()
    finally:
        await engine.dispose()

    print("PASS Binance BTCUSDT perpetual is registered for paper analysis")
    print("Live trading remains disarmed")


if __name__ == "__main__":
    asyncio.run(register())
