from decimal import Decimal
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from src.metrics import SaaSMetrics


def test_app_loads_and_renders_metrics_without_exceptions():
    engine = Mock()
    metrics = SaaSMetrics(
        mrr=Decimal("12500.00"),
        churn_rate=Decimal("0.025"),
        ltv=Decimal("5000.00"),
    )

    with (
        patch("src.database.create_database_engine", return_value=engine),
        patch("src.metrics.calculate_metrics", return_value=metrics) as calculator,
    ):
        app = AppTest.from_file("app.py").run(timeout=15)

        assert not app.exception
        assert app.title[0].value == "B2B SaaS Financial Metrics Dashboard"

        app.button[0].click().run(timeout=15)

        assert not app.exception
        assert len(app.metric) == 3
        calculator.assert_called_once()
