import os

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
)
from sqlalchemy.engine import Engine, URL


metadata = MetaData()

subscriptions = Table(
    "subscriptions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", String(255), nullable=False),
    Column("plan_name", String(255), nullable=False),
    Column("status", String(20), nullable=False),
    Column("mrr", Numeric(12, 2), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=True),
    CheckConstraint(
        "status IN ('active', 'canceled', 'past_due')",
        name="ck_subscriptions_status",
    ),
)


def _database_url_from_environment() -> URL:
    variable_names = (
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
    )
    values = {name: os.getenv(name) for name in variable_names}
    missing = [name for name, value in values.items() if not value]

    if missing:
        raise RuntimeError(
            f"Missing required database environment variables: {', '.join(missing)}"
        )

    return URL.create(
        drivername="postgresql+psycopg2",
        username=values["DB_USER"],
        password=values["DB_PASSWORD"],
        host=values["DB_HOST"],
        port=int(values["DB_PORT"]),
        database=values["DB_NAME"],
    )


def create_database_engine() -> Engine:
    return create_engine(_database_url_from_environment(), pool_pre_ping=True)


def initialize_database(engine: Engine) -> None:
    metadata.create_all(engine)
