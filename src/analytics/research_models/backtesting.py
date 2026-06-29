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
    score_column: str = "overall_score",
    two_stage: bool = True,
    minimum_return_rows: int = 252,
) -> list:
    """
    Select portfolio candidates from a larger ticker universe.

    Step 1: optional return-history eligibility filter.
    Step 2: rank all eligible tickers by factor score as of the rebalance date.
    Step 3: take top_screen_n.
    Step 4: optionally re-score that smaller group cross-sectionally.
    Step 5: return final_portfolio_n tickers for portfolio optimization.
    """

    eligible_tickers = filter_tickers_with_return_history(
        tickers=universe_tickers,
        as_of_date=as_of_date,
        minimum_return_rows=minimum_return_rows,
    )

    if not eligible_tickers:
        return []

    first_scores = calculate_factor_scores(
        eligible_tickers,
        as_of_date=as_of_date,
    )

    if first_scores.empty or score_column not in first_scores.columns:
        return []

    first_scores = first_scores.dropna(subset=[score_column])

    if first_scores.empty:
        return []

    first_scores = first_scores.set_index(score_column)
    first_scores = first_scores.sort_index(ascending=False)
    first_scores = first_scores.reset_index()

    screened_tickers = first_scores["ticker"].head(top_screen_n).tolist()

    if not two_stage:
        return screened_tickers[:final_portfolio_n]

    second_scores = calculate_factor_scores(
        screened_tickers,
        as_of_date=as_of_date,
    )

    if second_scores.empty or score_column not in second_scores.columns:
        return screened_tickers[:final_portfolio_n]

    second_scores = second_scores.dropna(subset=[score_column])

    if second_scores.empty:
        return screened_tickers[:final_portfolio_n]

    second_scores = second_scores.set_index(score_column)
    second_scores = second_scores.sort_index(ascending=False)
    second_scores = second_scores.reset_index()

    return second_scores["ticker"].head(final_portfolio_n).tolist()


def generate_rebalance_periods(
    start_date: date = date(2023, 1, 1),
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


# ---------------------------------------------------------------------
# Portfolio method construction
# ---------------------------------------------------------------------


def build_portfolio_weights(
    method_name: str,
    tickers: list,
    as_of_date: Optional[date] = None,
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
        )

    if method == "score_weighted":
        return score_weighted_portfolio(
            tickers=tickers,
            score_column=score_column,
            top_n=top_n,
            as_of_date=as_of_date,
        )

    if method == "risk_adjusted_score_weighted":
        return risk_adjusted_score_portfolio(
            tickers=tickers,
            score_column=score_column,
            risk_column=risk_column,
            top_n=top_n,
            as_of_date=as_of_date,
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
    start_date: date = date(2023, 1, 1),
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
) -> dict:
    """
    Run a rolling point-in-time backtest.

    Each rebalance:
    1. Select candidates from the full universe as of the rebalance date.
    2. Build weights using only data available as of the rebalance date.
    3. Hold those weights through the next rebalance window.
    """

    periods = generate_rebalance_periods(
        start_date=start_date,
        end_date=end_date,
        months=rebalance_months,
    )

    all_period_returns = []
    rebalance_history = []
    current_value = initial_value

    for period in periods:
        as_of = period["as_of_date"]
        period_start = period["start_date"]
        period_end = period["end_date"]

        selected_tickers = select_portfolio_candidates(
            universe_tickers=universe_tickers,
            as_of_date=as_of,
            top_screen_n=top_screen_n,
            final_portfolio_n=final_portfolio_n,
            score_column=score_column,
            two_stage=two_stage_selection,
            minimum_return_rows=minimum_return_rows,
        )

        if not selected_tickers:
            rebalance_history.append(
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

        weights = build_portfolio_weights(
            method_name=method_name,
            tickers=selected_tickers,
            as_of_date=as_of,
            top_n=min(top_n, len(selected_tickers)),
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

        if not weights:
            rebalance_history.append(
                {
                    "as_of_date": as_of,
                    "start_date": period_start,
                    "end_date": period_end,
                    "selected_tickers": selected_tickers,
                    "weights": {},
                    "period_return": None,
                    "ending_value": current_value,
                    "error": "Portfolio method returned empty weights.",
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
            rebalance_history.append(
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

        period_returns = calculate_portfolio_return_series(weights, returns)

        if period_returns.empty:
            rebalance_history.append(
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
        all_period_returns.append(period_returns)

        rebalance_history.append(
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

    if not all_period_returns:
        return {
            "method_name": method_name,
            "metrics": {},
            "equity_curve": [],
            "daily_returns": [],
            "rebalance_history": rebalance_history,
        }

    full_returns = pd.concat(all_period_returns).sort_index()
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

    return {
        "method_name": method_name,
        "metrics": metrics,
        "equity_curve": full_equity_curve.reset_index().to_dict(orient="records"),
        "daily_returns": full_returns.reset_index().to_dict(orient="records"),
        "rebalance_history": rebalance_history,
    }


def compare_rebalanced_portfolio_methods_backtest(
    universe_tickers: list,
    methods: Optional[list] = None,
    start_date: date = date(2023, 1, 1),
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
) -> dict:
    """Run rolling point-in-time backtests for multiple portfolio methods."""

    if methods is None:
        methods = get_default_portfolio_methods()

    results = {}

    for method_name in methods:
        try:
            results[method_name] = backtest_rebalanced_portfolio_method(
                universe_tickers=universe_tickers,
                method_name=method_name,
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
            )
        except Exception as error:
            results[method_name] = {
                "method_name": method_name,
                "metrics": {},
                "equity_curve": [],
                "daily_returns": [],
                "rebalance_history": [],
                "error": str(error),
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