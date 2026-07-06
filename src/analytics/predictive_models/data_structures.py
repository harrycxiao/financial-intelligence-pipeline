# src/analytics/predictive_models/data_structures.py

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from src.analytics.research_models.factor_models import calculate_factor_scores
from src.analytics.research_models.portfolio_models import get_returns_matrix


# ---------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------

PREDICTIVE_RESULTS_DIR = Path("results/predictive_model_data")
PREDICTIVE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TARGET_COLUMN = "forward_excess_return"
DEFAULT_DATE_COLUMN = "as_of_date"

DEFAULT_FACTOR_FEATURE_COLUMNS = [
    "overall_score",
    "value_score",
    "growth_score",
    "quality_score",
    "profitability_score",
    "financial_strength_score",
    "momentum_score",
    "risk_score",
]


# ---------------------------------------------------------------------
# General predictive-model dataframe helpers
# ---------------------------------------------------------------------

def normalize_quarter_dates(as_of_dates: list[date]) -> list[date]:
    """Return unique sorted as-of dates."""

    return sorted(set(as_of_dates))


def get_next_rebalance_date(
    as_of_date: date,
    all_as_of_dates: list[date],
) -> Optional[date]:
    """Find the next rebalance date after a given as-of date."""

    sorted_dates = normalize_quarter_dates(all_as_of_dates)

    for candidate_date in sorted_dates:
        if candidate_date > as_of_date:
            return candidate_date

    return None


def get_snapshot_path(as_of_date: date) -> Path:
    """Return the factor snapshot CSV path for one as-of date."""

    return PREDICTIVE_RESULTS_DIR / f"factor_snapshot_{as_of_date.isoformat()}.csv"


def build_factor_snapshot(
    tickers: list[str],
    as_of_date: date,
    period_mode: str = "quarterly",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Build or load one point-in-time factor snapshot.

    Output is passed into:
    - statistical_models.predict_statistical_expected_returns(...)
    - future ml_models prediction functions
    - future alpha_models ranking functions
    """

    snapshot_path = get_snapshot_path(as_of_date)

    if use_cache and snapshot_path.exists():
        return pd.read_csv(snapshot_path)

    snapshot = calculate_factor_scores(
        tickers=tickers,
        as_of_date=as_of_date,
        period_mode=period_mode,
    )

    if "ticker" not in snapshot.columns:
        raise ValueError("Factor snapshot must contain a 'ticker' column.")

    snapshot["as_of_date"] = as_of_date

    snapshot.to_csv(snapshot_path, index=False)

    return snapshot


def build_factor_snapshots(
    tickers: list[str],
    as_of_dates: list[date],
    period_mode: str = "quarterly",
    use_cache: bool = True,
) -> dict[date, pd.DataFrame]:
    """
    Build/load factor snapshots for multiple dates.

    This prevents recomputing expensive factor scores inside model loops.
    """

    snapshots = {}

    for as_of_date in normalize_quarter_dates(as_of_dates):
        snapshots[as_of_date] = build_factor_snapshot(
            tickers=tickers,
            as_of_date=as_of_date,
            period_mode=period_mode,
            use_cache=use_cache,
        )

    return snapshots


def calculate_forward_return_for_tickers(
    tickers: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Calculate forward holding-period returns for each ticker.

    This creates the target variable used by:
    - statistical_models.train_statistical_expected_return_model(...)
    - future ml_models training functions
    """

    returns = get_returns_matrix(tickers)
    returns.index = pd.to_datetime(returns.index)

    period_returns = returns.loc[
        (returns.index >= pd.to_datetime(start_date))
        & (returns.index <= pd.to_datetime(end_date))
    ].copy()

    rows = []

    for ticker in tickers:
        if ticker not in period_returns.columns:
            continue

        ticker_returns = period_returns[ticker].dropna()

        if ticker_returns.empty:
            continue

        forward_return = float((1.0 + ticker_returns).prod() - 1.0)

        rows.append(
            {
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date,
                "forward_return": forward_return,
            }
        )

    return pd.DataFrame(rows)


def calculate_benchmark_forward_return(
    benchmark_ticker: str,
    start_date: date,
    end_date: date,
) -> float:
    """Calculate benchmark forward return, usually SPY."""

    benchmark_df = calculate_forward_return_for_tickers(
        tickers=[benchmark_ticker],
        start_date=start_date,
        end_date=end_date,
    )

    if benchmark_df.empty:
        return 0.0

    return float(benchmark_df["forward_return"].iloc[0])


def add_forward_excess_returns(
    factor_snapshot: pd.DataFrame,
    start_date: date,
    end_date: date,
    benchmark_ticker: Optional[str] = "SPY",
) -> pd.DataFrame:
    """
    Add forward_return and forward_excess_return to one factor snapshot.

    This produces supervised learning rows:
    features at as_of_date -> future excess return over next quarter.
    """

    ticker_series = factor_snapshot["ticker"].dropna().astype(str)
    tickers: list[str] = [str(ticker).upper().strip() for ticker in ticker_series]

    forward_returns = calculate_forward_return_for_tickers(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
    )

    if benchmark_ticker is None:
        benchmark_return = 0.0
    else:
        benchmark_return = calculate_benchmark_forward_return(
            benchmark_ticker=benchmark_ticker,
            start_date=start_date,
            end_date=end_date,
        )

    forward_returns[DEFAULT_TARGET_COLUMN] = (
        forward_returns["forward_return"] - benchmark_return
    )

    merged = factor_snapshot.merge(
        forward_returns,
        on="ticker",
        how="inner",
    )

    return merged


def build_predictive_training_dataframe(
    tickers: list[str],
    as_of_dates: list[date],
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Build full ML-ready training dataframe.

    Output is directly passed into:
    - statistical_models.train_statistical_expected_return_model(...)
    - statistical_models.train_and_predict_statistical_expected_returns(...)
    - future ml_models train functions
    """

    sorted_dates = normalize_quarter_dates(as_of_dates)
    snapshots = build_factor_snapshots(
        tickers=tickers,
        as_of_dates=sorted_dates,
        period_mode=period_mode,
        use_cache=use_cache,
    )

    training_rows = []

    for as_of_date in sorted_dates:
        next_date = get_next_rebalance_date(
            as_of_date=as_of_date,
            all_as_of_dates=sorted_dates,
        )

        if next_date is None:
            continue

        factor_snapshot = snapshots[as_of_date]

        target_end_date = (pd.to_datetime(next_date) - pd.Timedelta(days=1)).date()

        labeled_snapshot = add_forward_excess_returns(
            factor_snapshot=factor_snapshot,
            start_date=as_of_date,
            end_date=target_end_date,
            benchmark_ticker=benchmark_ticker,
        )

        training_rows.append(labeled_snapshot)

    if not training_rows:
        return pd.DataFrame()

    training_df = pd.concat(training_rows, ignore_index=True)

    return training_df


def build_current_features_dataframe(
    tickers: list[str],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Build current feature dataframe for prediction.

    Output is passed into:
    - statistical_models.predict_statistical_expected_returns(...)
    - future ml_models predict functions
    """

    return build_factor_snapshot(
        tickers=tickers,
        as_of_date=current_as_of_date,
        period_mode=period_mode,
        use_cache=use_cache,
    )


def get_available_feature_columns(
    df: pd.DataFrame,
    preferred_columns: Optional[list[str]] = None,
) -> list[str]:
    """
    Return usable numeric feature columns.

    This lets statistical_models receive explicit feature_columns instead of
    relying only on infer_feature_columns(...).
    """

    if preferred_columns is None:
        preferred_columns = DEFAULT_FACTOR_FEATURE_COLUMNS

    available_columns = []

    for column in preferred_columns:
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            available_columns.append(column)

    return available_columns


# ---------------------------------------------------------------------
# Statistical model functions
# ---------------------------------------------------------------------

def build_statistical_model_training_data(
    tickers: list[str],
    as_of_dates: list[date],
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Build training_df and feature_columns for statistical_models.py.

    Pass outputs into:
    statistical_models.train_statistical_expected_return_model(
        training_df=training_df,
        feature_columns=feature_columns,
        target_column="forward_excess_return",
    )
    """

    training_df = build_predictive_training_dataframe(
        tickers=tickers,
        as_of_dates=as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    feature_columns = get_available_feature_columns(training_df)

    return training_df, feature_columns


def build_statistical_model_current_features(
    tickers: list[str],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Build current_features for statistical_models.py.

    Pass output into:
    statistical_models.predict_statistical_expected_returns(
        model=trained_statistical_model,
        current_features=current_features,
    )
    """

    return build_current_features_dataframe(
        tickers=tickers,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        use_cache=use_cache,
    )


def build_statistical_train_predict_inputs(
    tickers: list[str],
    training_as_of_dates: list[date],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Build all inputs needed by:
    statistical_models.train_and_predict_statistical_expected_returns(...)
    """

    training_df, feature_columns = build_statistical_model_training_data(
        tickers=tickers,
        as_of_dates=training_as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    current_features = build_statistical_model_current_features(
        tickers=tickers,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        use_cache=use_cache,
    )

    return training_df, current_features, feature_columns


# ---------------------------------------------------------------------
# ML model functions
# ---------------------------------------------------------------------

def build_ml_model_training_data(
    tickers: list[str],
    as_of_dates: list[date],
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Placeholder-compatible ML training dataframe builder.

    Later pass outputs into:
    ml_models.train_ml_expected_return_model(...)
    """

    return build_statistical_model_training_data(
        tickers=tickers,
        as_of_dates=as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )


def build_ml_model_current_features(
    tickers: list[str],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Placeholder-compatible ML current feature builder.

    Later pass output into:
    ml_models.predict_ml_expected_returns(...)
    """

    return build_current_features_dataframe(
        tickers=tickers,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        use_cache=use_cache,
    )


# ---------------------------------------------------------------------
# NLP model functions
# ---------------------------------------------------------------------

def build_nlp_model_training_data(
    tickers: list[str],
    as_of_dates: list[date],
    benchmark_ticker: Optional[str] = "SPY",
) -> pd.DataFrame:
    """
    Placeholder for NLP training data.

    Later this should join:
    - ticker
    - as_of_date
    - news/sentiment/filing features known before as_of_date
    - forward_excess_return target
    """

    raise NotImplementedError(
        "NLP training data builder is not implemented yet. "
        "Later, join news/filing sentiment features with forward_excess_return."
    )


def build_nlp_model_current_features(
    tickers: list[str],
    current_as_of_date: date,
) -> pd.DataFrame:
    """
    Placeholder for NLP current features.

    Later pass output into:
    nlp_models.predict_nlp_expected_returns(...)
    """

    raise NotImplementedError(
        "NLP current feature builder is not implemented yet. "
        "Later, build current news/filing sentiment features."
    )


# ---------------------------------------------------------------------
# Alpha model functions
# ---------------------------------------------------------------------

def build_alpha_model_base_inputs(
    tickers: list[str],
    training_as_of_dates: list[date],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> dict:
    """
    Build shared inputs for alpha_models.py.

    alpha_models.py can call this, then feed the returned dataframes into:
    - statistical_models.py
    - ml_models.py
    - nlp_models.py
    """

    statistical_training_df, statistical_current_features, statistical_features = (
        build_statistical_train_predict_inputs(
            tickers=tickers,
            training_as_of_dates=training_as_of_dates,
            current_as_of_date=current_as_of_date,
            period_mode=period_mode,
            benchmark_ticker=benchmark_ticker,
            use_cache=use_cache,
        )
    )

    return {
        "statistical_training_df": statistical_training_df,
        "statistical_current_features": statistical_current_features,
        "statistical_feature_columns": statistical_features,
        "target_column": DEFAULT_TARGET_COLUMN,
        "date_column": DEFAULT_DATE_COLUMN,
    }