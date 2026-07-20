#src/analytics/predictive_models/alpha_models.py

from datetime import date
from typing import Optional

import pandas as pd

from src.analytics.predictive_models.data_structures import (
    build_alpha_model_base_inputs,
)
from src.analytics.predictive_models.statistical_models import (
    train_and_predict_statistical_expected_returns,
)

STATISTICAL_ALPHA_COLUMN = "statistical_expected_excess_return"
FINAL_ALPHA_COLUMN = "alpha_expected_excess_return"


def add_current_date_to_training_boundaries(
    training_as_of_dates: list[date],
    current_as_of_date: date,
) -> list[date]:
    dates = list(training_as_of_dates)
    dates.append(current_as_of_date)

    return sorted(set(dates))


def calculate_alpha_expected_returns(
    tickers: list[str],
    training_as_of_dates: list[date],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
    min_train_periods: int = 8,
) -> pd.DataFrame:
    """
    Statistical alpha model.

    Uses the stacked statistical expected-return model with the eight
    engineered factor scores and exposes the final standardized alpha column.
    """

    training_dates_with_boundary = add_current_date_to_training_boundaries(
        training_as_of_dates=training_as_of_dates,
        current_as_of_date=current_as_of_date,
    )

    inputs = build_alpha_model_base_inputs(
        tickers=tickers,
        training_as_of_dates=training_dates_with_boundary,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    predictions = train_and_predict_statistical_expected_returns(
        training_df=inputs["statistical_training_df"],
        current_features=inputs["statistical_current_features"],
        feature_columns=inputs["statistical_feature_columns"],
        target_column=inputs["target_column"],
        date_column=inputs["date_column"],
        min_train_periods=min_train_periods,
    )

    if STATISTICAL_ALPHA_COLUMN not in predictions.columns:
        raise ValueError(
            f"Expected column '{STATISTICAL_ALPHA_COLUMN}' not found in predictions."
        )

    current_features = inputs["statistical_current_features"].copy()
    current_features["ticker"] = (
        current_features["ticker"].astype(str).str.upper().str.strip()
    )

    predictions = predictions.copy()
    predictions["ticker"] = predictions["ticker"].astype(str).str.upper().str.strip()

    result = current_features.merge(
        predictions,
        on="ticker",
        how="left",
    )

    result[FINAL_ALPHA_COLUMN] = result[STATISTICAL_ALPHA_COLUMN]
    result["as_of_date"] = current_as_of_date

    return result


def select_top_alpha_tickers(
    alpha_df: pd.DataFrame,
    top_n: int = 100,
    alpha_column: str = FINAL_ALPHA_COLUMN,
) -> list[str]:
    if alpha_df.empty:
        return []

    if "ticker" not in alpha_df.columns:
        raise ValueError("alpha_df must contain a 'ticker' column.")

    if alpha_column not in alpha_df.columns:
        raise ValueError(f"alpha_df must contain '{alpha_column}'.")

    ranked = alpha_df.dropna(subset=[alpha_column]).copy()
    ranked = ranked.sort_values(alpha_column, ascending=False)

    return ranked["ticker"].head(top_n).astype(str).str.upper().str.strip().tolist()