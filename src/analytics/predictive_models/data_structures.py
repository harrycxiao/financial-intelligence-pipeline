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

STATISTICAL_FEATURE_COLUMNS = [
    "value_score",
    "growth_score",
    "quality_score",
    "financial_strength_score",
    "efficiency_score",
    "momentum_score",
    "risk_score",
    "technical_score",
]

ML_FEATURE_COLUMNS = [
    "earnings_yield",
    "free_cash_flow_yield",
    "sales_yield",
    "book_to_market",
    "ev_to_sales",
    "ev_to_operating_income",
    "ev_to_ebitda",
    "ev_to_free_cash_flow",
    "revenue_growth",
    "net_income_growth",
    "free_cash_flow_growth",
    "revenue_cagr",
    "net_income_cagr",
    "free_cash_flow_cagr",
    "gross_margin",
    "operating_margin",
    "ebitda_margin",
    "net_margin",
    "free_cash_flow_margin",
    "return_on_assets",
    "return_on_equity",
    "return_on_invested_capital",
    "operating_cash_flow_to_net_income",
    "free_cash_flow_to_net_income",
    "debt_to_assets",
    "debt_to_equity",
    "net_debt_to_equity",
    "liabilities_to_assets",
    "cash_to_debt",
    "current_ratio",
    "quick_ratio",
    "interest_coverage",
    "asset_turnover",
    "r_and_d_intensity",
    "sga_intensity",
    "capex_to_revenue",
    "one_month_return",
    "three_month_return",
    "six_month_return",
    "one_year_return",
    "sharpe_ratio",
    "annualized_volatility",
    "max_drawdown",
    "beta_vs_spy",
    "price_vs_sma_50",
    "price_vs_sma_200",
    "sma_50_vs_sma_200",
    "macd_spread",
    "rsi_score",
    "volume_ratio",
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

def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add selected pairwise factor interaction features."""

    df = df.copy()

    df["quality_value_interaction"] = (
        pd.to_numeric(df["quality_score"], errors="coerce")
        * pd.to_numeric(df["value_score"], errors="coerce")
        / 100.0
    )

    df["growth_quality_interaction"] = (
        pd.to_numeric(df["growth_score"], errors="coerce")
        * pd.to_numeric(df["quality_score"], errors="coerce")
        / 100.0
    )

    df["momentum_technical_interaction"] = (
        pd.to_numeric(df["momentum_score"], errors="coerce")
        * pd.to_numeric(df["technical_score"], errors="coerce")
        / 100.0
    )

    df["financial_strength_quality_interaction"] = (
        pd.to_numeric(df["financial_strength_score"], errors="coerce")
        * pd.to_numeric(df["quality_score"], errors="coerce")
        / 100.0
    )

    df["value_financial_strength_interaction"] = (
        pd.to_numeric(df["value_score"], errors="coerce")
        * pd.to_numeric(df["financial_strength_score"], errors="coerce")
        / 100.0
    )

    df["growth_momentum_interaction"] = (
        pd.to_numeric(df["growth_score"], errors="coerce")
        * pd.to_numeric(df["momentum_score"], errors="coerce")
        / 100.0
    )

    df["efficiency_quality_interaction"] = (
        pd.to_numeric(df["efficiency_score"], errors="coerce")
        * pd.to_numeric(df["quality_score"], errors="coerce")
        / 100.0
    )

    df["risk_momentum_interaction"] = (
        pd.to_numeric(df["risk_score"], errors="coerce")
        * pd.to_numeric(df["momentum_score"], errors="coerce")
        / 100.0
    )

    return df

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

    snapshot = add_interaction_features(snapshot)

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
    min_period_return_rows: int = 55,
) -> pd.DataFrame:
    """Calculate forward holding-period returns for each ticker independently."""

    rows = []

    for ticker in tickers:
        clean_ticker = str(ticker).upper().strip()

        returns = get_returns_matrix([clean_ticker])

        if returns.empty or clean_ticker not in returns.columns:
            continue

        returns.index = pd.to_datetime(returns.index)

        ticker_returns = returns.loc[
            (returns.index >= pd.to_datetime(start_date))
            & (returns.index <= pd.to_datetime(end_date)),
            clean_ticker,
        ].dropna()

        if len(ticker_returns) < min_period_return_rows:
            continue

        forward_return = float((1.0 + ticker_returns).prod() - 1.0)

        rows.append(
            {
                "ticker": clean_ticker,
                "start_date": start_date,
                "end_date": end_date,
                "forward_return": forward_return,
                "period_return_rows": len(ticker_returns),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "ticker",
            "start_date",
            "end_date",
            "forward_return",
            "period_return_rows",
        ],
    )


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


def get_labeled_snapshot_path(
    as_of_date: date,
    start_date: date,
    end_date: date,
    benchmark_ticker: Optional[str],
) -> Path:
    benchmark = "none" if benchmark_ticker is None else benchmark_ticker.upper().strip()
    return (
        PREDICTIVE_RESULTS_DIR
        / f"labeled_snapshot_{as_of_date.isoformat()}_{start_date.isoformat()}_{end_date.isoformat()}_{benchmark}.csv"
    )


def add_forward_excess_returns(
    factor_snapshot: pd.DataFrame,
    start_date: date,
    end_date: date,
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Add forward_return and forward_excess_return to one factor snapshot.

    This produces supervised learning rows:
    features at as_of_date -> future excess return over next quarter.
    """
    as_of_date = pd.to_datetime(factor_snapshot["as_of_date"].iloc[0]).date()
    labeled_path = get_labeled_snapshot_path(
        as_of_date=as_of_date,
        start_date=start_date,
        end_date=end_date,
        benchmark_ticker=benchmark_ticker,
    )

    if use_cache and labeled_path.exists():
        return pd.read_csv(labeled_path)

    ticker_series = factor_snapshot["ticker"].dropna().astype(str)
    tickers: list[str] = [str(ticker).upper().strip() for ticker in ticker_series]

    forward_returns = calculate_forward_return_for_tickers(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
    )

    if forward_returns.empty:
        return pd.DataFrame()

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

    merged.to_csv(labeled_path, index=False)
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
            use_cache=use_cache,
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


def get_available_stats_feature_columns(
    df: pd.DataFrame,
    preferred_columns: Optional[list[str]] = None,
) -> list[str]:
    """
    Return usable numeric feature columns.

    This lets statistical_models receive explicit feature_columns instead of
    relying only on infer_feature_columns(...).
    """

    if preferred_columns is None:
        preferred_columns = STATISTICAL_FEATURE_COLUMNS

    available_columns = []

    for column in preferred_columns:
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            available_columns.append(column)

    return available_columns


def get_available_ml_feature_columns(
    df: pd.DataFrame,
    preferred_columns: Optional[list[str]] = None,
) -> list[str]:
    """
    Return usable numeric feature columns.

    This lets statistical_models receive explicit feature_columns instead of
    relying only on infer_feature_columns(...).
    """

    if preferred_columns is None:
        preferred_columns = ML_FEATURE_COLUMNS

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

    feature_columns = get_available_stats_feature_columns(training_df)

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

    training_df = build_predictive_training_dataframe(
        tickers=tickers,
        as_of_dates=as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    feature_columns = get_available_ml_feature_columns(training_df)

    return training_df, feature_columns


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

def build_ml_train_predict_inputs(
    tickers: list[str],
    training_as_of_dates: list[date],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Build all inputs needed by machine_learning_models.py."""

    training_df, feature_columns = build_ml_model_training_data(
        tickers=tickers,
        as_of_dates=training_as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    current_features = build_ml_model_current_features(
        tickers=tickers,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        use_cache=use_cache,
    )

    return training_df, current_features, feature_columns


# ---------------------------------------------------------------------
# Alpha model functions
# ---------------------------------------------------------------------

def build_alpha_model_training_data(
    tickers: list[str],
    as_of_dates: list[date],
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """
    Placeholder-compatible ML training dataframe builder.

    Later pass outputs into:
    ml_models.train_ml_expected_return_model(...)
    """

    training_df = build_predictive_training_dataframe(
        tickers=tickers,
        as_of_dates=as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    stats_feature_columns = get_available_stats_feature_columns(training_df)
    ml_feature_columns = get_available_ml_feature_columns(training_df)

    return training_df, stats_feature_columns, ml_feature_columns

def build_alpha_model_current_features(
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

def build_alpha_train_predict_inputs(
    tickers: list[str],
    training_as_of_dates: list[date],
    current_as_of_date: date,
    period_mode: str = "quarterly",
    benchmark_ticker: Optional[str] = "SPY",
    use_cache: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    """Build all inputs needed by machine_learning_models.py."""

    training_df, stats_feature_columns, ml_feature_columns = build_alpha_model_training_data(
        tickers=tickers,
        as_of_dates=training_as_of_dates,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    current_features = build_alpha_model_current_features(
        tickers=tickers,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        use_cache=use_cache,
    )

    return training_df, current_features, stats_feature_columns, ml_feature_columns

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

    ml_training_df, ml_current_features, ml_features = build_ml_train_predict_inputs(
        tickers=tickers,
        training_as_of_dates=training_as_of_dates,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    training_df, current_features, stats_feature_columns, ml_feature_columns = build_alpha_train_predict_inputs(
        tickers=tickers,
        training_as_of_dates=training_as_of_dates,
        current_as_of_date=current_as_of_date,
        period_mode=period_mode,
        benchmark_ticker=benchmark_ticker,
        use_cache=use_cache,
    )

    return {
        "statistical_training_df": statistical_training_df,
        "statistical_current_features": statistical_current_features,
        "statistical_feature_columns": statistical_features,
        "ml_training_df": ml_training_df,
        "ml_current_features": ml_current_features,
        "ml_feature_columns": ml_features,
        "combined_training_df": training_df,
        "combined_current_features": current_features,
        "combined_statistical_feature_columns": stats_feature_columns,
        "combined_ml_feature_columns": ml_feature_columns,
        "target_column": DEFAULT_TARGET_COLUMN,
        "date_column": DEFAULT_DATE_COLUMN,
    }


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

