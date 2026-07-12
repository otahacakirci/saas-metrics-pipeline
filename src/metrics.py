from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TypeAlias

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from src.database import subscriptions


TargetDate: TypeAlias = date | datetime | str | pd.Timestamp
ZERO = Decimal("0")
MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class SaaSMetrics:
    mrr: Decimal
    churn_rate: Decimal
    ltv: Decimal


def _normalize_target_date(target_date: TargetDate) -> pd.Timestamp:
    target = pd.Timestamp(target_date)

    if pd.isna(target):
        raise ValueError("target_date must be a valid date")

    if target.tzinfo is not None:
        target = target.tz_localize(None)

    return target.normalize()


def _load_subscriptions(engine: Engine) -> pd.DataFrame:
    dataframe = pd.read_sql(
        select(subscriptions),
        con=engine,
        coerce_float=False,
    )
    dataframe["start_date"] = pd.to_datetime(
        dataframe["start_date"], errors="coerce"
    )
    dataframe["end_date"] = pd.to_datetime(dataframe["end_date"], errors="coerce")
    dataframe["mrr"] = dataframe["mrr"].map(
        lambda value: Decimal(str(value)).quantize(MONEY_QUANTUM)
    )
    return dataframe


def _active_on(dataframe: pd.DataFrame, target: pd.Timestamp) -> pd.DataFrame:
    active_mask = (
        dataframe["status"].eq("active")
        & dataframe["start_date"].le(target)
        & (dataframe["end_date"].isna() | dataframe["end_date"].ge(target))
    )
    return dataframe.loc[active_mask]


def calculate_metrics(engine: Engine, target_date: TargetDate) -> SaaSMetrics:
    target = _normalize_target_date(target_date)
    dataframe = _load_subscriptions(engine)
    active_at_target = _active_on(dataframe, target)

    mrr = sum(active_at_target["mrr"], ZERO)
    active_customer_count = int(active_at_target["customer_id"].nunique())

    period_start = target.replace(day=1)
    next_period_start = period_start + pd.offsets.MonthBegin(1)
    active_at_period_start = dataframe.loc[
        dataframe["start_date"].le(period_start)
        & (
            dataframe["end_date"].isna()
            | dataframe["end_date"].ge(period_start)
        )
    ]
    active_at_period_start_count = int(
        active_at_period_start["customer_id"].nunique()
    )
    canceled_in_period = dataframe.loc[
        dataframe["status"].eq("canceled")
        & dataframe["end_date"].ge(period_start)
        & dataframe["end_date"].lt(next_period_start)
    ]
    canceled_customer_count = int(canceled_in_period["customer_id"].nunique())

    if active_at_period_start_count == 0:
        churn_rate = ZERO
    else:
        churn_rate = Decimal(canceled_customer_count) / Decimal(
            active_at_period_start_count
        )

    if active_customer_count == 0 or churn_rate == ZERO:
        ltv = ZERO
    else:
        average_mrr = mrr / Decimal(active_customer_count)
        ltv = average_mrr / churn_rate

    return SaaSMetrics(mrr=mrr, churn_rate=churn_rate, ltv=ltv)
