from datetime import date
from decimal import Decimal

from sqlalchemy import insert, select
from sqlalchemy.engine import make_url
from testcontainers.postgres import PostgresContainer

from src.database import create_database_engine, initialize_database, subscriptions


def test_subscription_can_be_stored_and_retrieved(monkeypatch):
    with PostgresContainer("postgres:16-alpine") as postgres:
        container_url = make_url(postgres.get_connection_url())
        database_environment = {
            "DB_HOST": container_url.host,
            "DB_PORT": str(container_url.port),
            "DB_USER": container_url.username,
            "DB_PASSWORD": container_url.password,
            "DB_NAME": container_url.database,
        }

        for name, value in database_environment.items():
            monkeypatch.setenv(name, value)

        engine = create_database_engine()

        try:
            initialize_database(engine)

            with engine.begin() as connection:
                connection.execute(
                    insert(subscriptions).values(
                        customer_id="customer-001",
                        plan_name="Growth",
                        status="active",
                        mrr=Decimal("149.90"),
                        start_date=date(2026, 7, 1),
                        end_date=None,
                    )
                )

            with engine.connect() as connection:
                subscription = connection.execute(
                    select(subscriptions).where(
                        subscriptions.c.customer_id == "customer-001"
                    )
                ).mappings().one()

            assert subscription["plan_name"] == "Growth"
            assert subscription["status"] == "active"
            assert subscription["mrr"] == Decimal("149.90")
            assert subscription["end_date"] is None
        finally:
            engine.dispose()
