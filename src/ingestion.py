from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd
from sqlalchemy.engine import Engine


RawSubscriptionData: TypeAlias = (
    pd.DataFrame
    | Mapping[str, Any]
    | Sequence[Mapping[str, Any]]
    | str
    | Path
)

SUBSCRIPTION_COLUMNS = (
    "customer_id",
    "plan_name",
    "status",
    "mrr",
    "start_date",
    "end_date",
)
REQUIRED_COLUMNS = set(SUBSCRIPTION_COLUMNS) - {"end_date"}
MONEY_QUANTUM = Decimal("0.01")
MAX_MRR_MAGNITUDE = Decimal("10000000000")


def _to_dataframe(raw_data: RawSubscriptionData) -> pd.DataFrame:
    if isinstance(raw_data, pd.DataFrame):
        return raw_data.copy(deep=True)

    if isinstance(raw_data, (str, Path)):
        path = Path(raw_data)
        readers = {
            ".csv": pd.read_csv,
            ".json": pd.read_json,
        }
        reader = readers.get(path.suffix.lower())

        if reader is None:
            raise ValueError("Subscription file must use a .csv or .json extension")

        return reader(path)

    if isinstance(raw_data, Mapping):
        try:
            return pd.DataFrame(raw_data)
        except ValueError:
            return pd.DataFrame([raw_data])

    return pd.DataFrame(raw_data)


def _normalize_date_column(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    normalized = parsed.dt.date.astype("object")
    return normalized.where(parsed.notna(), None)


def _normalize_mrr(value: Any) -> Decimal:
    if pd.isna(value):
        raise ValueError("MRR cannot be empty")

    try:
        amount = Decimal(str(value).strip().replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"Invalid MRR value: {value!r}") from error

    if not amount.is_finite():
        raise ValueError(f"Invalid MRR value: {value!r}")

    amount = amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

    if abs(amount) >= MAX_MRR_MAGNITUDE:
        raise ValueError(f"MRR value exceeds NUMERIC(12,2): {value!r}")

    return amount


def clean_subscription_data(raw_data: RawSubscriptionData) -> pd.DataFrame:
    dataframe = _to_dataframe(raw_data)
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))

    if missing:
        raise ValueError(f"Missing required subscription columns: {', '.join(missing)}")

    if "end_date" not in dataframe.columns:
        dataframe["end_date"] = None

    cleaned = dataframe.loc[:, SUBSCRIPTION_COLUMNS].copy()
    cleaned["start_date"] = _normalize_date_column(cleaned["start_date"])
    cleaned["end_date"] = _normalize_date_column(cleaned["end_date"])

    invalid_start_dates = cleaned["start_date"].isna()
    if invalid_start_dates.any():
        invalid_rows = cleaned.index[invalid_start_dates].tolist()
        raise ValueError(f"Invalid start_date values at rows: {invalid_rows}")

    cleaned["mrr"] = cleaned["mrr"].map(_normalize_mrr)
    return cleaned


def ingest_subscriptions(raw_data: RawSubscriptionData, engine: Engine) -> int:
    cleaned = clean_subscription_data(raw_data)

    cleaned.to_sql(
        "subscriptions",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    return len(cleaned)
