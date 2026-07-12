from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy.engine import make_url
from testcontainers.postgres import PostgresContainer

from src.database import create_database_engine, initialize_database
from src.ingestion import ingest_subscriptions
from src.metrics import calculate_metrics


def test_core_saas_metrics_are_calculated_exactly(monkeypatch):
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
                        "customer_id": "customer-active-before-period",
                        "plan_name": "Growth",
                        "status": "active",
                        "mrr": "100.00",
                        "start_date": "2026-06-01",
                        "end_date": None,
                    },
                    {
                        "customer_id": "customer-active-during-period",
                        "plan_name": "Scale",
                        "status": "active",
                        "mrr": "200.00",
                        "start_date": "2026-07-10",
                        "end_date": None,
                    },
                    {
                        "customer_id": "customer-churned-in-period",
                        "plan_name": "Starter",
                        "status": "canceled",
                        "mrr": "50.00",
                        "start_date": "2026-05-01",
                        "end_date": "2026-07-15",
                    },
                    {
                        "customer_id": "customer-churned-before-period",
                        "plan_name": "Starter",
                        "status": "canceled",
                        "mrr": "75.00",
                        "start_date": "2026-03-01",
                        "end_date": "2026-06-20",
                    },
                ]
            )
            ingest_subscriptions(raw_subscriptions, engine)

            july_metrics = calculate_metrics(engine, date(2026, 7, 31))
            august_metrics = calculate_metrics(engine, date(2026, 8, 31))

            assert july_metrics.mrr == Decimal("300.00")
            assert july_metrics.churn_rate == Decimal("0.5")
            assert july_metrics.ltv == Decimal("300.00")
            assert august_metrics.mrr == Decimal("300.00")
            assert august_metrics.churn_rate == Decimal("0")
            assert august_metrics.ltv == Decimal("0")
        finally:
            engine.dispose()
