from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from olive.config import get_settings
from olive.db import Base
from olive.domain import models  # noqa: F401
from olive.execution_risk import models as execution_risk_models  # noqa: F401
from olive.gateway import models as gateway_models  # noqa: F401
from olive.market_data import models as market_data_models  # noqa: F401
from olive.risk import models as risk_models  # noqa: F401
from olive.validation import models as validation_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata
ENUM_CHECK_NAMES = {
    "account_environment",
    "account_status",
    "asset_class",
    "asset_status",
    "instrument_status",
    "instrument_type",
    "portfolio_status",
    "strategy_status",
    "strategy_version_state",
    "signal_direction",
    "signal_environment",
    "signal_intake_status",
    "underlying_asset_class",
    "underlying_status",
    "venue_instrument_status",
    "venue_status",
}


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    _reflected: bool,
    compare_to: object | None,
) -> bool:
    """Ignore dialect-sensitive type-bound enum checks during schema comparison."""
    if type_ == "check_constraint" and (
        name in ENUM_CHECK_NAMES
        or getattr(object_, "_type_bound", False)
        or getattr(compare_to, "_type_bound", False)
    ):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
