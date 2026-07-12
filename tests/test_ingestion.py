from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import make_url
from testcontainers.postgres import PostgresContainer

from src.database import create_database_engine, initialize_database, subscriptions
from src.ingestion import ingest_subscriptions


def test_dirty_subscription_data_is_cleaned_and_bulk_inserted(monkeypatch):
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
            raw_subscriptions = pd.DataFrame(
                [
                    {
                        "customer_id": "customer-001",
                        "plan_name": "Growth",
                        "status": "active",
                        "mrr": "1,249.90",
                        "start_date": "2026-07-01",
                        "end_date": "2026-12-31",
                    },
                    {
                        "customer_id": "customer-002",
                        "plan_name": "Starter",
                        "status": "past_due",
                        "mrr": 79.995,
                        "start_date": "07/15/2026",
                        "end_date": "not-a-date",
                    },
                ]
            )

            inserted_count = ingest_subscriptions(raw_subscriptions, engine)

            with engine.connect() as connection:
                stored_subscriptions = connection.execute(
                    select(subscriptions).order_by(subscriptions.c.customer_id)
                ).mappings().all()

            assert inserted_count == 2
            assert len(stored_subscriptions) == 2
            assert stored_subscriptions[0]["mrr"] == Decimal("1249.90")
            assert stored_subscriptions[0]["start_date"] == date(2026, 7, 1)
            assert stored_subscriptions[0]["end_date"] == date(2026, 12, 31)
            assert stored_subscriptions[1]["mrr"] == Decimal("80.00")
            assert stored_subscriptions[1]["start_date"] == date(2026, 7, 15)
            assert stored_subscriptions[1]["end_date"] is None
        finally:
            engine.dispose()
