# src/analytics/research_engine.py

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from src.analytics.predictive_models import (
    FINAL_ALPHA_COLUMN,
    calculate_alpha_expected_returns,
)
from src.analytics.research_models.factor_models import (
    calculate_factor_scores,
)
from src.analytics.research_models.portfolio_models import (
    equal_weight_portfolio,
    get_returns_matrix,
    hierarchical_risk_parity_portfolio,
    maximum_sharpe_portfolio,
    mean_variance_portfolio,
    minimum_variance_portfolio,
    risk_adjusted_score_portfolio,
    risk_parity_portfolio,
    score_weighted_portfolio,
    top_n_equal_weight_portfolio,
)


@dataclass
class ResearchEngineConfig:
    """Configuration for one point-in-time quantitative research run."""

    period_mode: str = "quarterly"

    top_screen_n: int = 100
    final_portfolio_n: int = 5
    minimum_return_rows: int = 252

    training_lookback_periods: int = 12
    training_period_months: int = 3
    min_train_periods: int = 8
    benchmark_ticker: Optional[str] = "SPY"

    portfolio_method: str = "score_weighted"
    covariance_method: str = "sample"
    ewma_span: int = 60

    max_weight: Optional[float] = 1.0
    risk_aversion: float = 1.0
    risk_free_signal: float = 0.0

    hrp_linkage_method: str = "single"
    hrp_use_expected_return_signal: bool = True
    hrp_return_risk_metric: str = "volatility"

    use_cache: bool = True


def clean_ticker_list(tickers: list[str]) -> list[str]:
    """Normalize tickers and remove duplicates while preserving order."""

    clean_tickers = []
    seen = set()

    for ticker in tickers:
        clean_ticker = str(ticker).upper().strip()

        if not clean_ticker or clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        clean_tickers.append(clean_ticker)

    return clean_tickers


def filter_eligible_tickers(
    tickers: list[str],
    as_of_date: date,
    minimum_return_rows: int = 252,
) -> list[str]:
    """Keep tickers with enough return history as of the research date."""

    eligible_tickers = []

    for ticker in clean_ticker_list(tickers):
        returns = get_returns_matrix(
            tickers=[ticker],
            as_of_date=as_of_date,
        )

        if len(returns) >= minimum_return_rows:
            eligible_tickers.append(ticker)

    return eligible_tickers


def generate_training_as_of_dates(
    current_as_of_date: date,
    lookback_periods: int = 12,
    months: int = 3,
) -> list[date]:
    """Generate historical as-of dates used to train predictive models."""

    dates = pd.date_range(
        end=pd.to_datetime(current_as_of_date) - pd.DateOffset(months=months),
        periods=lookback_periods,
        freq=f"{months}MS",
    )

    return [timestamp.date() for timestamp in dates]


def rank_factor_universe(
    tickers: list[str],
    as_of_date: date,
    top_screen_n: int = 100,
    final_portfolio_n: int = 5,
    period_mode: str = "quarterly",
) -> dict:
    """
    Apply the two-stage factor-selection process.

    Stage 1:
        Rank the complete eligible universe and retain the top screen.

    Stage 2:
        Recalculate cross-sectional factor scores within the screened
        universe and retain the final portfolio candidates.
    """

    full_factor_scores = calculate_factor_scores(
        tickers=tickers,
        as_of_date=as_of_date,
        period_mode=period_mode,
    )

    if full_factor_scores.empty:
        return {
            "full_factor_scores": pd.DataFrame(),
            "screened_factor_scores": pd.DataFrame(),
            "screened_tickers": [],
            "selected_tickers": [],
        }

    required_columns = {"ticker", "overall_score"}

    if not required_columns.issubset(full_factor_scores.columns):
        raise ValueError(
            "Factor-score dataframe must contain 'ticker' and 'overall_score'."
        )

    full_factor_scores = full_factor_scores.copy()
    full_factor_scores["ticker"] = (
        full_factor_scores["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    full_factor_scores = (
        full_factor_scores
        .dropna(subset=["overall_score"])
        .sort_values("overall_score", ascending=False)
        .reset_index(drop=True)
    )

    screened_tickers = (
        full_factor_scores["ticker"]
        .head(top_screen_n)
        .tolist()
    )

    if not screened_tickers:
        return {
            "full_factor_scores": full_factor_scores,
            "screened_factor_scores": pd.DataFrame(),
            "screened_tickers": [],
            "selected_tickers": [],
        }

    screened_factor_scores = calculate_factor_scores(
        tickers=screened_tickers,
        as_of_date=as_of_date,
        period_mode=period_mode,
    )

    if screened_factor_scores.empty:
        return {
            "full_factor_scores": full_factor_scores,
            "screened_factor_scores": pd.DataFrame(),
            "screened_tickers": screened_tickers,
            "selected_tickers": screened_tickers[:final_portfolio_n],
        }

    screened_factor_scores = screened_factor_scores.copy()
    screened_factor_scores["ticker"] = (
        screened_factor_scores["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    screened_factor_scores = (
        screened_factor_scores
        .dropna(subset=["overall_score"])
        .sort_values("overall_score", ascending=False)
        .reset_index(drop=True)
    )

    selected_tickers = (
        screened_factor_scores["ticker"]
        .head(final_portfolio_n)
        .tolist()
    )

    return {
        "full_factor_scores": full_factor_scores,
        "screened_factor_scores": screened_factor_scores,
        "screened_tickers": screened_tickers,
        "selected_tickers": selected_tickers,
    }


def build_research_portfolio_weights(
    tickers: list[str],
    scores_df: pd.DataFrame,
    as_of_date: date,
    config: ResearchEngineConfig,
) -> dict[str, float]:
    """
    Construct final portfolio weights.

    Selection has already been completed using factors. The statistical
    expected-return signal is used only by methods that require a return
    signal.
    """

    method = config.portfolio_method.lower().strip()
    top_n = min(config.final_portfolio_n, len(tickers))

    if method == "equal_weight":
        return equal_weight_portfolio(tickers)

    if method == "top_n_equal_weight":
        return top_n_equal_weight_portfolio(
            tickers=tickers,
            n=top_n,
            score_column=FINAL_ALPHA_COLUMN,
            as_of_date=as_of_date,
            period_mode=config.period_mode,
            scores_df=scores_df,
        )

    if method == "score_weighted":
        return score_weighted_portfolio(
            tickers=tickers,
            score_column=FINAL_ALPHA_COLUMN,
            top_n=top_n,
            as_of_date=as_of_date,
            period_mode=config.period_mode,
            scores_df=scores_df,
        )

    if method == "risk_adjusted_score_weighted":
        return risk_adjusted_score_portfolio(
            tickers=tickers,
            score_column=FINAL_ALPHA_COLUMN,
            risk_column="annualized_volatility",
            top_n=top_n,
            as_of_date=as_of_date,
            period_mode=config.period_mode,
            scores_df=scores_df,
        )

    if method == "minimum_variance":
        return minimum_variance_portfolio(
            tickers=tickers,
            max_weight=config.max_weight,
            long_only=True,
            covariance_method=config.covariance_method,
            ewma_span=config.ewma_span,
            as_of_date=as_of_date,
        )

    if method == "maximum_sharpe":
        return maximum_sharpe_portfolio(
            tickers=tickers,
            score_column=FINAL_ALPHA_COLUMN,
            risk_free_signal=config.risk_free_signal,
            max_weight=config.max_weight,
            long_only=True,
            covariance_method=config.covariance_method,
            ewma_span=config.ewma_span,
            as_of_date=as_of_date,
            period_mode=config.period_mode,
            scores_df=scores_df,
        )

    if method == "mean_variance":
        return mean_variance_portfolio(
            tickers=tickers,
            risk_aversion=config.risk_aversion,
            score_column=FINAL_ALPHA_COLUMN,
            max_weight=config.max_weight,
            long_only=True,
            covariance_method=config.covariance_method,
            ewma_span=config.ewma_span,
            as_of_date=as_of_date,
            period_mode=config.period_mode,
            scores_df=scores_df,
        )

    if method == "risk_parity":
        return risk_parity_portfolio(
            tickers=tickers,
            max_weight=config.max_weight,
            covariance_method=config.covariance_method,
            ewma_span=config.ewma_span,
            as_of_date=as_of_date,
        )

    if method == "hierarchical_risk_parity":
        return hierarchical_risk_parity_portfolio(
            tickers=tickers,
            max_weight=config.max_weight,
            linkage_method=config.hrp_linkage_method,
            covariance_method=config.covariance_method,
            ewma_span=config.ewma_span,
            use_expected_return_signal=config.hrp_use_expected_return_signal,
            score_column=FINAL_ALPHA_COLUMN,
            return_risk_metric=config.hrp_return_risk_metric,
            as_of_date=as_of_date,
            period_mode=config.period_mode,
            scores_df=scores_df,
        )

    raise ValueError(f"Unknown portfolio method: {config.portfolio_method}")


def run_research_engine(
    universe_tickers: list[str],
    as_of_date: date,
    config: Optional[ResearchEngineConfig] = None,
) -> dict:
    """
    Run the complete point-in-time quantitative research workflow.

    Workflow:
    1. Normalize and filter the ticker universe.
    2. Rank the full universe using factor scores.
    3. Recalculate factor scores within the top screen.
    4. Select the final portfolio candidates using factors.
    5. Estimate statistical expected excess returns.
    6. Construct final portfolio weights.
    7. Return all major intermediate and final research outputs.
    """

    if config is None:
        config = ResearchEngineConfig()

    clean_universe = clean_ticker_list(universe_tickers)

    eligible_tickers = filter_eligible_tickers(
        tickers=clean_universe,
        as_of_date=as_of_date,
        minimum_return_rows=config.minimum_return_rows,
    )

    if not eligible_tickers:
        raise ValueError(
            "No eligible tickers had sufficient return history."
        )

    factor_results = rank_factor_universe(
        tickers=eligible_tickers,
        as_of_date=as_of_date,
        top_screen_n=config.top_screen_n,
        final_portfolio_n=config.final_portfolio_n,
        period_mode=config.period_mode,
    )

    selected_tickers = factor_results["selected_tickers"]

    if not selected_tickers:
        raise ValueError(
            "Factor selection did not produce any portfolio candidates."
        )

    training_as_of_dates = generate_training_as_of_dates(
        current_as_of_date=as_of_date,
        lookback_periods=config.training_lookback_periods,
        months=config.training_period_months,
    )

    alpha_scores = calculate_alpha_expected_returns(
        tickers=eligible_tickers,
        training_as_of_dates=training_as_of_dates,
        current_as_of_date=as_of_date,
        period_mode=config.period_mode,
        benchmark_ticker=config.benchmark_ticker,
        use_cache=config.use_cache,
        min_train_periods=config.min_train_periods,
    )

    if alpha_scores.empty:
        raise ValueError(
            "Statistical expected-return model returned no predictions."
        )

    alpha_scores = alpha_scores.copy()
    alpha_scores["ticker"] = (
        alpha_scores["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    selected_set = set(selected_tickers)

    selected_alpha_scores = alpha_scores[
        alpha_scores["ticker"].isin(selected_set)
    ].copy()

    final_factor_scores = factor_results["screened_factor_scores"][
        factor_results["screened_factor_scores"]["ticker"].isin(selected_set)
    ].copy()

    selected_research = final_factor_scores.merge(
        selected_alpha_scores[
            ["ticker", FINAL_ALPHA_COLUMN]
        ],
        on="ticker",
        how="left",
    )

    selected_research = selected_research.sort_values(
        "overall_score",
        ascending=False,
    ).reset_index(drop=True)

    weights = build_research_portfolio_weights(
        tickers=selected_tickers,
        scores_df=selected_alpha_scores,
        as_of_date=as_of_date,
        config=config,
    )

    return {
        "as_of_date": as_of_date,
        "configuration": {
            "period_mode": config.period_mode,
            "top_screen_n": config.top_screen_n,
            "final_portfolio_n": config.final_portfolio_n,
            "minimum_return_rows": config.minimum_return_rows,
            "training_lookback_periods": config.training_lookback_periods,
            "portfolio_method": config.portfolio_method,
            "covariance_method": config.covariance_method,
            "max_weight": config.max_weight,
        },
        "universe_size": len(clean_universe),
        "eligible_universe_size": len(eligible_tickers),
        "eligible_tickers": eligible_tickers,
        "training_as_of_dates": training_as_of_dates,
        "full_factor_scores": factor_results["full_factor_scores"],
        "screened_factor_scores": factor_results["screened_factor_scores"],
        "screened_tickers": factor_results["screened_tickers"],
        "selected_tickers": selected_tickers,
        "alpha_scores": alpha_scores,
        "selected_research": selected_research,
        "portfolio_weights": weights,
    }
