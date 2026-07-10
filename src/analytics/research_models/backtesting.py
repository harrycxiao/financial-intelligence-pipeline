# src/analytics/research_models/backtesting.py

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from src.analytics.research_models.factor_models import calculate_factor_scores
from src.analytics.research_models.portfolio_models import (
    equal_weight_portfolio,
    top_n_equal_weight_portfolio,
    score_weighted_portfolio,
    risk_adjusted_score_portfolio,
    minimum_variance_portfolio,
    maximum_sharpe_portfolio,
    mean_variance_portfolio,
    risk_parity_portfolio,
    hierarchical_risk_parity_portfolio,
    get_returns_matrix,
)

from src.analytics.predictive_models.alpha_models import (
    calculate_alpha_expected_returns,
    FINAL_ALPHA_COLUMN,
)


# ---------------------------------------------------------------------
# Return / equity curve helpers
# ---------------------------------------------------------------------


def filter_returns_by_date(
    returns: pd.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Filter return matrix to a date range."""

    if returns.empty:
        return returns

    filtered = returns.copy()
    filtered.index = pd.to_datetime(filtered.index)

    if start_date is not None:
        filtered = filtered.loc[filtered.index >= pd.to_datetime(start_date), :].copy()

    if end_date is not None:
        filtered = filtered.loc[filtered.index <= pd.to_datetime(end_date), :].copy()

    return filtered

def build_cash_return_series(
    reference_tickers: list,
    start_date: date,
    end_date: date,
) -> pd.Series:
    """
    Build a zero-return series over the actual trading dates in a holding period.

    Used when the strategy deliberately holds cash because the portfolio
    construction method produces no investable long-only weights.
    """

    for ticker in reference_tickers:
        returns = get_returns_matrix([ticker])

        if returns.empty:
            continue

        returns = filter_returns_by_date(
            returns=returns,
            start_date=start_date,
            end_date=end_date,
        )

        if not returns.empty:
            return pd.Series(
                0.0,
                index=returns.index,
                name="portfolio_return",
                dtype=float,
            )

    # Defensive fallback if none of the selected tickers has usable dates.
    fallback_dates = pd.bdate_range(
        start=pd.to_datetime(start_date),
        end=pd.to_datetime(end_date),
    )

    return pd.Series(
        0.0,
        index=fallback_dates,
        name="portfolio_return",
        dtype=float,
    )


def align_weights_to_returns(weights: dict, returns: pd.DataFrame) -> pd.Series:
    """Align portfolio weights to available return columns."""

    if returns.empty or not weights:
        return pd.Series(dtype=float)

    aligned = pd.Series(
        {ticker: weights.get(ticker, 0.0) for ticker in returns.columns},
        dtype=float,
    )

    return aligned


def calculate_portfolio_return_series(
    weights: dict,
    returns: pd.DataFrame,
) -> pd.Series:
    """Calculate daily portfolio returns from fixed weights and asset returns."""

    if returns.empty or not weights:
        return pd.Series(dtype=float)

    aligned_weights = align_weights_to_returns(weights, returns)

    if aligned_weights.empty:
        return pd.Series(dtype=float)

    return pd.Series(
        returns.to_numpy(dtype=float) @ aligned_weights.to_numpy(dtype=float),
        index=returns.index,
        name="portfolio_return",
    )


def calculate_equity_curve(
    portfolio_returns: pd.Series,
    initial_value: float = 1.0,
) -> pd.Series:
    """Convert daily returns into a cumulative equity curve."""

    if portfolio_returns.empty:
        return pd.Series(dtype=float)

    return initial_value * (1 + portfolio_returns.fillna(0)).cumprod()


def calculate_max_drawdown_from_equity(equity_curve: pd.Series) -> Optional[float]:
    """Calculate max drawdown from an equity curve."""

    if equity_curve.empty:
        return None

    running_max = equity_curve.cummax()
    drawdowns = (equity_curve - running_max) / running_max
    max_drawdown = drawdowns.min()

    if pd.isna(max_drawdown):
        return None

    return float(max_drawdown)


def calculate_backtest_metrics(
    portfolio_returns: pd.Series,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> dict:
    """Calculate standard backtest performance metrics."""

    if portfolio_returns.empty:
        return {}

    clean_returns = portfolio_returns.dropna()

    if clean_returns.empty:
        return {}

    equity_curve = calculate_equity_curve(clean_returns)

    start_value = float(equity_curve.iloc[0])
    end_value = float(equity_curve.iloc[-1])

    total_return = end_value / start_value - 1 if start_value != 0 else None

    periods = len(clean_returns)
    years = periods / trading_days

    annualized_return = (
        (1 + total_return) ** (1 / years) - 1
        if total_return is not None and years > 0 and total_return > -1
        else None
    )

    annualized_volatility = float(clean_returns.std() * np.sqrt(trading_days))

    excess_annualized_return = (
        annualized_return - risk_free_rate
        if annualized_return is not None
        else None
    )

    sharpe_ratio = (
        excess_annualized_return / annualized_volatility
        if excess_annualized_return is not None and annualized_volatility != 0
        else None
    )

    max_drawdown = calculate_max_drawdown_from_equity(equity_curve)

    winning_days = clean_returns[clean_returns > 0]
    win_rate = len(winning_days) / len(clean_returns) if len(clean_returns) > 0 else None

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "risk_free_rate": risk_free_rate,
        "excess_annualized_return": excess_annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "average_daily_return": float(clean_returns.mean()),
        "best_day": float(clean_returns.max()),
        "worst_day": float(clean_returns.min()),
        "number_of_days": periods,
    }


# ---------------------------------------------------------------------
# Universe / candidate selection helpers
# ---------------------------------------------------------------------


def clean_ticker_list(tickers: list) -> list:
    """Normalize tickers and remove duplicates while preserving order."""

    seen = set()
    clean_tickers = []

    for ticker in tickers:
        clean_ticker = str(ticker).upper().strip()

        if not clean_ticker or clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        clean_tickers.append(clean_ticker)

    return clean_tickers


def filter_tickers_with_return_history(
    tickers: list,
    as_of_date: date,
    minimum_return_rows: int = 252,
) -> list:
    """
    Keep tickers with enough stored return history as of a date.

    This is a lightweight eligibility filter before factor scoring.
    """

    eligible = []

    for ticker in clean_ticker_list(tickers):
        returns = get_returns_matrix(
            [ticker],
            as_of_date=as_of_date,
        )

        if len(returns) >= minimum_return_rows:
            eligible.append(ticker)

    return eligible


def select_portfolio_candidates(
    universe_tickers: list,
    as_of_date: date,
    top_screen_n: int = 100,
    final_portfolio_n: int = 10,
    first_stage_mode: str = "factor",
    second_stage_mode: str = "factor",
    factor_score_column: str = "overall_score",
    alpha_score_column: str = FINAL_ALPHA_COLUMN,
    minimum_return_rows: int = 252,
    factor_scores_df: Optional[pd.DataFrame] = None,
    alpha_scores_df: Optional[pd.DataFrame] = None,
) -> list:
    """Select candidates using precomputed factor/alpha score dataframes."""

    eligible_tickers = filter_tickers_with_return_history(
        tickers=universe_tickers,
        as_of_date=as_of_date,
        minimum_return_rows=minimum_return_rows,
    )

    if not eligible_tickers:
        return []

    eligible_set = set(eligible_tickers)

    def prepare_scores(
        scores_df: Optional[pd.DataFrame],
        score_column: str,
        allowed_tickers: set,
    ) -> pd.DataFrame:
        if scores_df is None or scores_df.empty:
            return pd.DataFrame()

        if "ticker" not in scores_df.columns or score_column not in scores_df.columns:
            return pd.DataFrame()

        df = scores_df.copy()
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        df = df[df["ticker"].isin(allowed_tickers)].copy()
        df = df[df[score_column].notna()].copy()

        if df.empty:
            return df

        df = df.set_index(score_column)
        df = df.sort_index(ascending=False)
        df = df.reset_index()

        return df

    first_stage_mode = first_stage_mode.lower().strip()
    second_stage_mode = second_stage_mode.lower().strip()

    if first_stage_mode == "factor":
        if factor_scores_df is None:
            factor_scores_df = calculate_factor_scores(
                eligible_tickers,
                as_of_date=as_of_date,
                period_mode="quarterly",
            )

        first_scores = prepare_scores(
            scores_df=factor_scores_df,
            score_column=factor_score_column,
            allowed_tickers=eligible_set,
        )

    elif first_stage_mode == "alpha":
        first_scores = prepare_scores(
            scores_df=alpha_scores_df,
            score_column=alpha_score_column,
            allowed_tickers=eligible_set,
        )

    else:
        raise ValueError("first_stage_mode must be 'factor' or 'alpha'.")

    if first_scores.empty:
        return []

    screened_tickers = (
        first_scores["ticker"]
        .head(top_screen_n)
        .astype(str)
        .str.upper()
        .str.strip()
        .tolist()
    )

    if not screened_tickers:
        return []

    screened_set = set(screened_tickers)

    if second_stage_mode == "factor":
        second_raw_scores = calculate_factor_scores(
            screened_tickers,
            as_of_date=as_of_date,
            period_mode="quarterly",
        )

        second_scores = prepare_scores(
            scores_df=second_raw_scores,
            score_column=factor_score_column,
            allowed_tickers=screened_set,
        )

    elif second_stage_mode == "alpha":
        second_scores = prepare_scores(
            scores_df=alpha_scores_df,
            score_column=alpha_score_column,
            allowed_tickers=screened_set,
        )

    else:
        raise ValueError("second_stage_mode must be 'factor' or 'alpha'.")

    if second_scores.empty:
        return screened_tickers[:final_portfolio_n]

    return second_scores["ticker"].head(final_portfolio_n).tolist()


def generate_rebalance_periods(
    start_date: date = date(2024, 4, 1),
    end_date: date = date(2026, 3, 31),
    months: int = 3,
) -> list[dict]:
    """
    Generate rolling rebalance windows.

    Default creates 13 quarterly windows:
    2023 Q1 through 2026 Q1.
    """

    starts = pd.date_range(
        start=pd.to_datetime(start_date),
        end=pd.to_datetime(end_date),
        freq=f"{months}MS",
    )

    periods = []

    for i, start_timestamp in enumerate(starts):
        period_start = start_timestamp.date()

        if i + 1 < len(starts):
            next_start = starts[i + 1].date()
            period_end = (pd.to_datetime(next_start) - pd.Timedelta(days=1)).date()
        else:
            period_end = end_date

        if period_start > end_date:
            continue

        if period_end > end_date:
            period_end = end_date

        periods.append(
            {
                "as_of_date": period_start,
                "start_date": period_start,
                "end_date": period_end,
            }
        )

    return periods

def generate_training_as_of_dates(
    current_as_of_date: date,
    lookback_periods: int = 12,
    months: int = 3,
) -> list[date]:
    """Generate prior rebalance as-of dates for predictive-model training."""

    dates = pd.date_range(
        end=pd.to_datetime(current_as_of_date) - pd.DateOffset(months=months),
        periods=lookback_periods,
        freq=f"{months}MS",
    )

    return [timestamp.date() for timestamp in dates]


# ---------------------------------------------------------------------
# Portfolio method construction
# ---------------------------------------------------------------------


def build_portfolio_weights(
    method_name: str,
    tickers: list,
    as_of_date: Optional[date] = None,
    period_mode: str = "quarterly",
    top_n: int = 5,
    score_column: str = FINAL_ALPHA_COLUMN,
    risk_column: str = "annualized_volatility",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    risk_aversion: float = 3.0,
    risk_free_signal: float = 0.0,
    risk_parity_max_iterations: int = 1000,
    risk_parity_tolerance: float = 1e-8,
    hrp_linkage_method: str = "single",
    hrp_use_expected_return_signal: bool = True,
    hrp_return_risk_metric: str = "volatility",
    scores_df: Optional[pd.DataFrame] = None,
) -> dict:
    """Build portfolio weights for one named portfolio construction method."""

    method = method_name.lower().strip()

    if method == "equal_weight":
        return equal_weight_portfolio(tickers)

    if method == "top_n_equal_weight":
        return top_n_equal_weight_portfolio(
            tickers=tickers,
            n=top_n,
            score_column=score_column,
            as_of_date=as_of_date,
            period_mode=period_mode,
            scores_df=scores_df,
        )

    if method == "score_weighted":
        return score_weighted_portfolio(
            tickers=tickers,
            score_column=score_column,
            top_n=top_n,
            as_of_date=as_of_date,
            period_mode=period_mode,
            scores_df=scores_df,
        )

    if method == "risk_adjusted_score_weighted":
        return risk_adjusted_score_portfolio(
            tickers=tickers,
            score_column=score_column,
            risk_column=risk_column,
            top_n=top_n,
            as_of_date=as_of_date,
            period_mode=period_mode,
            scores_df=scores_df,
        )

    if method == "minimum_variance":
        return minimum_variance_portfolio(
            tickers=tickers,
            max_weight=max_weight,
            long_only=long_only,
            max_abs_weight=max_abs_weight,
            exposure_mode=exposure_mode,
            target_gross_exposure=target_gross_exposure,
            target_net_exposure=target_net_exposure,
            covariance_method=covariance_method,
            ewma_span=ewma_span,
            as_of_date=as_of_date,
        )

    if method == "maximum_sharpe":
        return maximum_sharpe_portfolio(
            tickers=tickers,
            score_column=score_column,
            risk_free_signal=risk_free_signal,
            max_weight=max_weight,
            long_only=long_only,
            max_abs_weight=max_abs_weight,
            exposure_mode=exposure_mode,
            target_gross_exposure=target_gross_exposure,
            target_net_exposure=target_net_exposure,
            covariance_method=covariance_method,
            ewma_span=ewma_span,
            as_of_date=as_of_date,
            period_mode=period_mode,
            scores_df=scores_df,
        )

    if method == "mean_variance":
        return mean_variance_portfolio(
            tickers=tickers,
            risk_aversion=risk_aversion,
            score_column=score_column,
            max_weight=max_weight,
            long_only=long_only,
            max_abs_weight=max_abs_weight,
            exposure_mode=exposure_mode,
            target_net_exposure=target_net_exposure,
            covariance_method=covariance_method,
            ewma_span=ewma_span,
            as_of_date=as_of_date,
            period_mode=period_mode,
            scores_df=scores_df,
        )

    if method == "risk_parity":
        return risk_parity_portfolio(
            tickers=tickers,
            max_weight=max_weight,
            max_iterations=risk_parity_max_iterations,
            tolerance=risk_parity_tolerance,
            covariance_method=covariance_method,
            ewma_span=ewma_span,
            as_of_date=as_of_date,
        )

    if method == "hierarchical_risk_parity":
        return hierarchical_risk_parity_portfolio(
            tickers=tickers,
            max_weight=max_weight,
            linkage_method=hrp_linkage_method,
            covariance_method=covariance_method,
            ewma_span=ewma_span,
            use_expected_return_signal=hrp_use_expected_return_signal,
            score_column=score_column,
            return_risk_metric=hrp_return_risk_metric,
            as_of_date=as_of_date,
            period_mode=period_mode,
            scores_df=scores_df,
        )

    raise ValueError(f"Unknown portfolio method: {method_name}")


# ---------------------------------------------------------------------
# Fixed-weight / single-period backtesting
# ---------------------------------------------------------------------


def backtest_fixed_weight_portfolio(
    weights: dict,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    initial_value: float = 1.0,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> dict:
    """Backtest one fixed-weight portfolio over a historical period."""

    tickers = list(weights.keys())
    returns = get_returns_matrix(tickers)
    returns = filter_returns_by_date(returns, start_date, end_date)

    if returns.empty:
        return {
            "weights": weights,
            "metrics": {},
            "equity_curve": [],
            "daily_returns": [],
        }

    portfolio_returns = calculate_portfolio_return_series(weights, returns)
    equity_curve = calculate_equity_curve(portfolio_returns, initial_value)

    metrics = calculate_backtest_metrics(
        portfolio_returns=portfolio_returns,
        risk_free_rate=risk_free_rate,
        trading_days=trading_days,
    )

    return {
        "weights": weights,
        "metrics": metrics,
        "equity_curve": equity_curve.reset_index().to_dict(orient="records"),
        "daily_returns": portfolio_returns.reset_index().to_dict(orient="records"),
    }


def backtest_portfolio_method(
    tickers: list,
    method_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    as_of_date: Optional[date] = None,
    period_mode: str = "quarterly",
    initial_value: float = 1.0,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
    top_n: int = 5,
    score_column: str = "overall_score",
    risk_column: str = "annualized_volatility",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    risk_aversion: float = 3.0,
    risk_free_signal: float = 0.0,
    risk_parity_max_iterations: int = 1000,
    risk_parity_tolerance: float = 1e-8,
    hrp_linkage_method: str = "single",
    hrp_use_expected_return_signal: bool = True,
    hrp_return_risk_metric: str = "volatility",
) -> dict:
    """Construct weights using one method and backtest them."""

    weights = build_portfolio_weights(
        method_name=method_name,
        tickers=tickers,
        as_of_date=as_of_date,
        period_mode=period_mode,
        top_n=top_n,
        score_column=score_column,
        risk_column=risk_column,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        max_weight=max_weight,
        long_only=long_only,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_gross_exposure,
        target_net_exposure=target_net_exposure,
        risk_aversion=risk_aversion,
        risk_free_signal=risk_free_signal,
        risk_parity_max_iterations=risk_parity_max_iterations,
        risk_parity_tolerance=risk_parity_tolerance,
        hrp_linkage_method=hrp_linkage_method,
        hrp_use_expected_return_signal=hrp_use_expected_return_signal,
        hrp_return_risk_metric=hrp_return_risk_metric,
    )

    result = backtest_fixed_weight_portfolio(
        weights=weights,
        start_date=start_date,
        end_date=end_date,
        initial_value=initial_value,
        risk_free_rate=risk_free_rate,
        trading_days=trading_days,
    )

    result["method_name"] = method_name
    result["as_of_date"] = as_of_date
    result["selected_tickers"] = list(weights.keys())

    return result


def compare_portfolio_methods_backtest(
    tickers: list,
    methods: Optional[list] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    as_of_date: Optional[date] = None,
    period_mode: str = "quarterly",
    initial_value: float = 1.0,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
    top_n: int = 5,
    score_column: str = "overall_score",
    risk_column: str = "annualized_volatility",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    risk_aversion: float = 3.0,
    risk_free_signal: float = 0.0,
    risk_parity_max_iterations: int = 1000,
    risk_parity_tolerance: float = 1e-8,
    hrp_linkage_method: str = "single",
    hrp_use_expected_return_signal: bool = True,
    hrp_return_risk_metric: str = "volatility",
) -> dict:
    """Backtest and compare multiple portfolio construction methods."""

    if methods is None:
        methods = get_default_portfolio_methods()

    results = {}

    for method_name in methods:
        try:
            results[method_name] = backtest_portfolio_method(
                tickers=tickers,
                method_name=method_name,
                start_date=start_date,
                end_date=end_date,
                as_of_date=as_of_date,
                period_mode=period_mode,
                initial_value=initial_value,
                risk_free_rate=risk_free_rate,
                trading_days=trading_days,
                top_n=top_n,
                score_column=score_column,
                risk_column=risk_column,
                covariance_method=covariance_method,
                ewma_span=ewma_span,
                max_weight=max_weight,
                long_only=long_only,
                max_abs_weight=max_abs_weight,
                exposure_mode=exposure_mode,
                target_gross_exposure=target_gross_exposure,
                target_net_exposure=target_net_exposure,
                risk_aversion=risk_aversion,
                risk_free_signal=risk_free_signal,
                risk_parity_max_iterations=risk_parity_max_iterations,
                risk_parity_tolerance=risk_parity_tolerance,
                hrp_linkage_method=hrp_linkage_method,
                hrp_use_expected_return_signal=hrp_use_expected_return_signal,
                hrp_return_risk_metric=hrp_return_risk_metric,
            )
        except Exception as error:
            results[method_name] = {
                "method_name": method_name,
                "weights": {},
                "metrics": {},
                "equity_curve": [],
                "daily_returns": [],
                "selected_tickers": [],
                "error": str(error),
            }

    summary = build_backtest_comparison_table(results)

    return {
        "results": results,
        "summary": summary.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------
# Rolling / rebalanced backtesting
# ---------------------------------------------------------------------


def backtest_rebalanced_portfolio_method(
    universe_tickers: list,
    method_name: str,
    start_date: date = date(2024, 4, 1),
    end_date: date = date(2026, 3, 31),
    rebalance_months: int = 3,
    initial_value: float = 1.0,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
    top_screen_n: int = 100,
    final_portfolio_n: int = 10,
    two_stage_selection: bool = True,
    minimum_return_rows: int = 252,
    top_n: int = 5,
    score_column: str = "overall_score",
    risk_column: str = "annualized_volatility",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    risk_aversion: float = 3.0,
    risk_free_signal: float = 0.0,
    risk_parity_max_iterations: int = 1000,
    risk_parity_tolerance: float = 1e-8,
    hrp_linkage_method: str = "single",
    hrp_use_expected_return_signal: bool = True,
    hrp_return_risk_metric: str = "volatility",
    period_mode: str = "quarterly",
) -> dict:
    """
    Run a rolling point-in-time backtest for one method.

    This wrapper is kept for single-method use.
    For multi-method comparisons, use compare_rebalanced_portfolio_methods_backtest(),
    which avoids recomputing selected candidates for each method.
    """

    comparison = compare_rebalanced_portfolio_methods_backtest(
        universe_tickers=universe_tickers,
        methods=[method_name],
        start_date=start_date,
        end_date=end_date,
        rebalance_months=rebalance_months,
        initial_value=initial_value,
        risk_free_rate=risk_free_rate,
        trading_days=trading_days,
        top_screen_n=top_screen_n,
        final_portfolio_n=final_portfolio_n,
        two_stage_selection=two_stage_selection,
        minimum_return_rows=minimum_return_rows,
        top_n=top_n,
        score_column=score_column,
        risk_column=risk_column,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        max_weight=max_weight,
        long_only=long_only,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_gross_exposure,
        target_net_exposure=target_net_exposure,
        risk_aversion=risk_aversion,
        risk_free_signal=risk_free_signal,
        risk_parity_max_iterations=risk_parity_max_iterations,
        risk_parity_tolerance=risk_parity_tolerance,
        hrp_linkage_method=hrp_linkage_method,
        hrp_use_expected_return_signal=hrp_use_expected_return_signal,
        hrp_return_risk_metric=hrp_return_risk_metric,
        period_mode=period_mode,
    )

    return comparison["results"].get(
        method_name,
        {
            "method_name": method_name,
            "metrics": {},
            "equity_curve": [],
            "daily_returns": [],
            "rebalance_history": [],
            "error": "Method result not found.",
        },
    )


def compare_rebalanced_portfolio_methods_backtest(
    universe_tickers: list,
    methods: Optional[list] = None,
    start_date: date = date(2024, 4, 1),
    end_date: date = date(2026, 3, 31),
    rebalance_months: int = 3,
    initial_value: float = 1.0,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
    top_screen_n: int = 100,
    final_portfolio_n: int = 10,
    two_stage_selection: bool = True,
    minimum_return_rows: int = 252,
    top_n: int = 5,
    score_column: str = FINAL_ALPHA_COLUMN,
    risk_column: str = "annualized_volatility",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    risk_aversion: float = 3.0,
    risk_free_signal: float = 0.0,
    risk_parity_max_iterations: int = 1000,
    risk_parity_tolerance: float = 1e-8,
    hrp_linkage_method: str = "single",
    hrp_use_expected_return_signal: bool = True,
    hrp_return_risk_metric: str = "volatility",
    period_mode: str = "quarterly",
) -> dict:
    """
    Run rolling point-in-time backtests for multiple portfolio methods.

    Optimized structure:
    each rebalance date selects candidates once, then reuses the same
    selected ticker list across all portfolio methods.
    """

    if methods is None:
        methods = get_default_portfolio_methods()

    periods = generate_rebalance_periods(
        start_date=start_date,
        end_date=end_date,
        months=rebalance_months,
    )

    method_state = {}

    for method_name in methods:
        method_state[method_name] = {
            "method_name": method_name,
            "current_value": initial_value,
            "period_returns": [],
            "rebalance_history": [],
            "error": None,
        }

    for period in periods:
        as_of = period["as_of_date"]
        period_start = period["start_date"]
        period_end = period["end_date"]

        training_as_of_dates = generate_training_as_of_dates(
            current_as_of_date=as_of,
            lookback_periods=12,
            months=rebalance_months,
        )

        combined_scores_df = calculate_alpha_expected_returns(
            tickers=universe_tickers,
            training_as_of_dates=training_as_of_dates,
            current_as_of_date=as_of,
            period_mode=period_mode,
            benchmark_ticker="SPY",
            use_cache=True,
            min_train_periods=8,
        )

        combined_scores_df["ticker"] = (
            combined_scores_df["ticker"].astype(str).str.upper().str.strip()
        )

        selected_tickers = select_portfolio_candidates(
            universe_tickers=universe_tickers,
            as_of_date=as_of,
            top_screen_n=top_screen_n,
            final_portfolio_n=final_portfolio_n,
            first_stage_mode="factor",
            second_stage_mode="factor",
            factor_scores_df=combined_scores_df,
            alpha_scores_df=combined_scores_df,
            factor_score_column="overall_score",
            alpha_score_column=FINAL_ALPHA_COLUMN,
            minimum_return_rows=minimum_return_rows,
        )

        for method_name in methods:
            state = method_state[method_name]
            current_value = state["current_value"]

            if not selected_tickers:
                state["rebalance_history"].append(
                    {
                        "as_of_date": as_of,
                        "start_date": period_start,
                        "end_date": period_end,
                        "selected_tickers": [],
                        "weights": {},
                        "period_return": None,
                        "ending_value": current_value,
                        "error": "No selected tickers.",
                    }
                )
                continue

            try:
                weights = build_portfolio_weights(
                    method_name=method_name,
                    tickers=selected_tickers,
                    as_of_date=as_of,
                    top_n=min(top_n, len(selected_tickers)),
                    risk_column=risk_column,
                    covariance_method=covariance_method,
                    ewma_span=ewma_span,
                    max_weight=max_weight,
                    long_only=long_only,
                    max_abs_weight=max_abs_weight,
                    exposure_mode=exposure_mode,
                    target_gross_exposure=target_gross_exposure,
                    target_net_exposure=target_net_exposure,
                    risk_aversion=risk_aversion,
                    risk_free_signal=risk_free_signal,
                    risk_parity_max_iterations=risk_parity_max_iterations,
                    risk_parity_tolerance=risk_parity_tolerance,
                    hrp_linkage_method=hrp_linkage_method,
                    hrp_use_expected_return_signal=hrp_use_expected_return_signal,
                    hrp_return_risk_metric=hrp_return_risk_metric,
                    score_column=score_column,
                    scores_df=combined_scores_df,
                )

                if not weights:
                    cash_returns = build_cash_return_series(
                            reference_tickers=selected_tickers,
                            start_date=period_start,
                            end_date=period_end,
                        )

                    state["period_returns"].append(cash_returns)

                    state["rebalance_history"].append(
                        {
                            "as_of_date": as_of,
                            "start_date": period_start,
                            "end_date": period_end,
                            "selected_tickers": selected_tickers,
                            "weights": {},
                            "period_return": 0.0,
                            "ending_value": current_value,
                            "error": None,
                            "position_status": "cash",
                            "cash_reason": (
                                "Portfolio method produced no positive long-only weights."
                            ),
                        }
                    )
                    continue

                returns = get_returns_matrix(list(weights.keys()))
                returns = filter_returns_by_date(
                    returns=returns,
                    start_date=period_start,
                    end_date=period_end,
                )

                if returns.empty:
                    state["rebalance_history"].append(
                        {
                            "as_of_date": as_of,
                            "start_date": period_start,
                            "end_date": period_end,
                            "selected_tickers": selected_tickers,
                            "weights": weights,
                            "period_return": None,
                            "ending_value": current_value,
                            "error": "No returns during holding window.",
                        }
                    )
                    continue

                period_returns = calculate_portfolio_return_series(
                    weights=weights,
                    returns=returns,
                )

                if period_returns.empty:
                    state["rebalance_history"].append(
                        {
                            "as_of_date": as_of,
                            "start_date": period_start,
                            "end_date": period_end,
                            "selected_tickers": selected_tickers,
                            "weights": weights,
                            "period_return": None,
                            "ending_value": current_value,
                            "error": "Could not calculate portfolio returns.",
                        }
                    )
                    continue

                period_equity = calculate_equity_curve(
                    portfolio_returns=period_returns,
                    initial_value=current_value,
                )

                period_return = (
                    float(period_equity.iloc[-1] / current_value - 1)
                    if current_value != 0
                    else None
                )

                current_value = float(period_equity.iloc[-1])
                state["current_value"] = current_value
                state["period_returns"].append(period_returns)

                state["rebalance_history"].append(
                    {
                        "as_of_date": as_of,
                        "start_date": period_start,
                        "end_date": period_end,
                        "selected_tickers": selected_tickers,
                        "weights": weights,
                        "period_return": period_return,
                        "ending_value": current_value,
                        "error": None,
                    }
                )

            except Exception as error:
                state["rebalance_history"].append(
                    {
                        "as_of_date": as_of,
                        "start_date": period_start,
                        "end_date": period_end,
                        "selected_tickers": selected_tickers,
                        "weights": {},
                        "period_return": None,
                        "ending_value": current_value,
                        "error": str(error),
                    }
                )

                if state["error"] is None:
                    state["error"] = str(error)

    results = {}

    for method_name, state in method_state.items():
        period_returns_list = state["period_returns"]

        if not period_returns_list:
            results[method_name] = {
                "method_name": method_name,
                "metrics": {},
                "equity_curve": [],
                "daily_returns": [],
                "rebalance_history": state["rebalance_history"],
                "error": state["error"],
            }
            continue

        full_returns = pd.concat(period_returns_list).sort_index()
        full_returns.name = "portfolio_return"

        full_equity_curve = calculate_equity_curve(
            portfolio_returns=full_returns,
            initial_value=initial_value,
        )

        metrics = calculate_backtest_metrics(
            portfolio_returns=full_returns,
            risk_free_rate=risk_free_rate,
            trading_days=trading_days,
        )

        results[method_name] = {
            "method_name": method_name,
            "metrics": metrics,
            "equity_curve": full_equity_curve.reset_index().to_dict(orient="records"),
            "daily_returns": full_returns.reset_index().to_dict(orient="records"),
            "rebalance_history": state["rebalance_history"],
            "error": state["error"],
        }

    summary = build_backtest_comparison_table(results)

    return {
        "results": results,
        "summary": summary.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------
# Result comparison helpers
# ---------------------------------------------------------------------


def get_default_portfolio_methods() -> list:
    """Return all supported portfolio construction methods."""

    return [
        "equal_weight",
        "top_n_equal_weight",
        "score_weighted",
        "risk_adjusted_score_weighted",
        "minimum_variance",
        "maximum_sharpe",
        "mean_variance",
        "risk_parity",
        "hierarchical_risk_parity",
    ]


def build_backtest_comparison_table(results: dict) -> pd.DataFrame:
    """Build a comparison table from method backtest results."""

    rows = []

    for method_name, result in results.items():
        metrics = result.get("metrics", {})

        row = {
            "method_name": method_name,
            "total_return": metrics.get("total_return"),
            "annualized_return": metrics.get("annualized_return"),
            "annualized_volatility": metrics.get("annualized_volatility"),
            "sharpe_ratio": metrics.get("sharpe_ratio"),
            "max_drawdown": metrics.get("max_drawdown"),
            "win_rate": metrics.get("win_rate"),
            "number_of_days": metrics.get("number_of_days"),
            "error": result.get("error"),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    if "sharpe_ratio" in df.columns:
        df = df.set_index("sharpe_ratio")
        df = df.sort_index(ascending=False, na_position="last")
        df = df.reset_index()

    return df.reset_index(drop=True)