from datetime import date
from decimal import Decimal

import streamlit as st

from src.database import create_database_engine
from src.metrics import SaaSMetrics, calculate_metrics


ZERO = Decimal("0")


@st.cache_resource
def get_database_engine():
    return create_database_engine()


def format_currency(value: Decimal) -> str:
    return f"${value:,.2f}"


def format_percentage(value: Decimal) -> str:
    return f"{value * Decimal('100'):,.2f}%"


def render_metrics(metrics: SaaSMetrics) -> None:
    mrr_column, churn_column, ltv_column = st.columns(3)
    mrr_column.metric("MRR", format_currency(metrics.mrr))
    churn_column.metric("Churn Rate", format_percentage(metrics.churn_rate))
    ltv_column.metric("LTV", format_currency(metrics.ltv))

    if ZERO in (metrics.mrr, metrics.churn_rate, metrics.ltv):
        st.info(
            "Se?ilen d?nem i?in baz? metrikler yeterli aktif abonelik verisi "
            "olmad???ndan 0 olarak hesapland?."
        )


def main() -> None:
    st.set_page_config(
        page_title="B2B SaaS Financial Metrics Dashboard",
        page_icon="??",
        layout="wide",
    )
    st.title("B2B SaaS Financial Metrics Dashboard")
    target_date = st.date_input("Hedef tarih", value=date.today())

    try:
        engine = get_database_engine()
    except Exception:
        st.error(
            "Veritaban? ba?lant?s? kurulamad?. L?tfen ortam yap?land?rmas?n? "
            "kontrol edin."
        )
        return

    if st.button("Metrikleri Hesapla", type="primary"):
        try:
            metrics = calculate_metrics(engine, target_date)
        except Exception:
            st.error(
                "Metrikler ?u anda hesaplanam?yor. L?tfen daha sonra tekrar deneyin."
            )
            return

        render_metrics(metrics)


if __name__ == "__main__":
    main()
