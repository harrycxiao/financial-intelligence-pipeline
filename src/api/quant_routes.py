# src/api/quant_routes.py

from datetime import date, datetime
import math
from typing import Any, Literal, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.analytics import (
    ResearchEngineConfig,
    run_research_engine,
)


router = APIRouter(
    prefix="/api/quant",
    tags=["quantitative research"],
)


PortfolioMethod = Literal[
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

PeriodMode = Literal[
    "quarterly",
    "annual",
    "raw",
]

CovarianceMethod = Literal[
    "sample",
    "ewma",
    "ledoit_wolf",
    "oas",
]

HRPLinkageMethod = Literal[
    "single",
    "complete",
    "average",
    "weighted",
]

HRPRiskMetric = Literal[
    "volatility",
    "variance",
]


class QuantResearchRequest(BaseModel):
    """
    Input for one point-in-time quantitative research run.

    The ticker universe is screened using factor scores. The final selected
    stocks are then assigned portfolio weights using the requested portfolio
    construction method.
    """

    tickers: list[str] = Field(
        ...,
        min_length=1,
        description="Ticker universe to analyze.",
    )

    as_of_date: date = Field(
        ...,
        description="Point-in-time research date.",
    )

    period_mode: PeriodMode = "quarterly"

    top_screen_n: int = Field(
        default=100,
        ge=1,
        description="Number of stocks retained after the first factor screen.",
    )

    final_portfolio_n: int = Field(
        default=5,
        ge=1,
        description="Number of stocks selected for the final portfolio.",
    )

    minimum_return_rows: int = Field(
        default=252,
        ge=1,
        description="Minimum number of historical daily-return rows required.",
    )

    training_lookback_periods: int = Field(
        default=12,
        ge=2,
        description="Number of historical rebalance periods used for training.",
    )

    training_period_months: int = Field(
        default=3,
        ge=1,
        description="Months between predictive-model training dates.",
    )

    min_train_periods: int = Field(
        default=8,
        ge=2,
        description="Minimum number of periods before OOF prediction begins.",
    )

    benchmark_ticker: Optional[str] = Field(
        default="SPY",
        description="Benchmark used to calculate forward excess returns.",
    )

    portfolio_method: PortfolioMethod = "score_weighted"
    covariance_method: CovarianceMethod = "sample"

    ewma_span: int = Field(
        default=60,
        ge=2,
    )

    max_weight: Optional[float] = Field(
        default=1.0,
        gt=0.0,
        le=1.0,
    )

    risk_aversion: float = Field(
        default=1.0,
        ge=1.0,
    )

    risk_free_signal: float = 0.04

    hrp_linkage_method: HRPLinkageMethod = "single"
    hrp_use_expected_return_signal: bool = True
    hrp_return_risk_metric: HRPRiskMetric = "volatility"

    use_cache: bool = True

    include_full_results: bool = Field(
        default=False,
        description=(
            "Include full-universe factor scores and all alpha predictions. "
            "These can make the response much larger."
        ),
    )

    class Config:
        extra = "forbid"


def normalize_tickers(tickers: list[str]) -> list[str]:
    """Normalize request tickers and remove duplicates."""

    clean_tickers = []
    seen = set()

    for ticker in tickers:
        clean_ticker = str(ticker).upper().strip()

        if not clean_ticker or clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        clean_tickers.append(clean_ticker)

    return clean_tickers


def to_json_safe(value: Any) -> Any:
    """
    Recursively convert Pandas, NumPy, date, and missing values into
    JSON-serializable Python values.
    """

    if value is None:
        return None

    if isinstance(value, pd.DataFrame):
        return to_json_safe(value.to_dict(orient="records"))

    if isinstance(value, pd.Series):
        return to_json_safe(value.to_dict())

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, np.ndarray):
        return to_json_safe(value.tolist())

    if isinstance(value, np.generic):
        return to_json_safe(value.item())

    if isinstance(value, dict):
        return {
            str(key): to_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(item) for item in value]

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

        return value

    try:
        missing = pd.isna(value)

        if isinstance(missing, (bool, np.bool_)) and missing:
            return None
    except (TypeError, ValueError):
        pass

    return value


def build_research_response(
    result: dict,
    include_full_results: bool,
) -> dict:
    """
    Build a compact response by default.

    Full-universe factor and alpha tables are returned only when explicitly
    requested because they may contain thousands of rows.
    """

    response = {
        "as_of_date": result.get("as_of_date"),
        "configuration": result.get("configuration", {}),
        "universe_size": result.get("universe_size"),
        "eligible_universe_size": result.get("eligible_universe_size"),
        "training_as_of_dates": result.get("training_as_of_dates", []),
        "screened_tickers": result.get("screened_tickers", []),
        "selected_tickers": result.get("selected_tickers", []),
        "selected_research": result.get("selected_research", pd.DataFrame()),
        "portfolio_weights": result.get("portfolio_weights", {}),
    }

    if include_full_results:
        response.update(
            {
                "eligible_tickers": result.get("eligible_tickers", []),
                "full_factor_scores": result.get(
                    "full_factor_scores",
                    pd.DataFrame(),
                ),
                "screened_factor_scores": result.get(
                    "screened_factor_scores",
                    pd.DataFrame(),
                ),
                "alpha_scores": result.get(
                    "alpha_scores",
                    pd.DataFrame(),
                ),
            }
        )

    return to_json_safe(response)


@router.get("/research/defaults")
def get_quant_research_defaults() -> dict:
    """
    Return the default settings used by the quantitative research engine.

    This is useful for dashboards and AI agents that need to discover the
    normal research configuration before submitting a run.
    """

    config = ResearchEngineConfig()

    return {
        "period_mode": config.period_mode,
        "top_screen_n": config.top_screen_n,
        "final_portfolio_n": config.final_portfolio_n,
        "minimum_return_rows": config.minimum_return_rows,
        "training_lookback_periods": config.training_lookback_periods,
        "training_period_months": config.training_period_months,
        "min_train_periods": config.min_train_periods,
        "benchmark_ticker": config.benchmark_ticker,
        "portfolio_method": config.portfolio_method,
        "covariance_method": config.covariance_method,
        "ewma_span": config.ewma_span,
        "max_weight": config.max_weight,
        "risk_aversion": config.risk_aversion,
        "risk_free_signal": config.risk_free_signal,
        "hrp_linkage_method": config.hrp_linkage_method,
        "hrp_use_expected_return_signal": (
            config.hrp_use_expected_return_signal
        ),
        "hrp_return_risk_metric": config.hrp_return_risk_metric,
        "use_cache": config.use_cache,
    }


@router.post("/research/run")
def run_quant_research(request: QuantResearchRequest) -> dict:
    """
    Run one point-in-time quantitative research pipeline.

    The response includes:
    - factor-screened stocks;
    - final selected stocks;
    - statistical expected excess returns;
    - selected-stock research data;
    - final portfolio weights.
    """

    tickers = normalize_tickers(request.tickers)

    if not tickers:
        raise HTTPException(
            status_code=400,
            detail="At least one valid ticker must be provided.",
        )

    if request.final_portfolio_n > request.top_screen_n:
        raise HTTPException(
            status_code=400,
            detail=(
                "final_portfolio_n cannot be greater than top_screen_n."
            ),
        )

    if request.top_screen_n > len(tickers):
        raise HTTPException(
            status_code=400,
            detail=(
                "top_screen_n cannot be greater than the number of "
                "unique tickers provided."
            ),
        )

    config = ResearchEngineConfig(
        period_mode=request.period_mode,
        top_screen_n=request.top_screen_n,
        final_portfolio_n=request.final_portfolio_n,
        minimum_return_rows=request.minimum_return_rows,
        training_lookback_periods=request.training_lookback_periods,
        training_period_months=request.training_period_months,
        min_train_periods=request.min_train_periods,
        benchmark_ticker=(
            request.benchmark_ticker.upper().strip()
            if request.benchmark_ticker
            else None
        ),
        portfolio_method=request.portfolio_method,
        covariance_method=request.covariance_method,
        ewma_span=request.ewma_span,
        max_weight=request.max_weight,
        risk_aversion=request.risk_aversion,
        risk_free_signal=request.risk_free_signal,
        hrp_linkage_method=request.hrp_linkage_method,
        hrp_use_expected_return_signal=(
            request.hrp_use_expected_return_signal
        ),
        hrp_return_risk_metric=request.hrp_return_risk_metric,
        use_cache=request.use_cache,
    )

    try:
        result = run_research_engine(
            universe_tickers=tickers,
            as_of_date=request.as_of_date,
            config=config,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "The quantitative research run failed: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error

    return build_research_response(
        result=result,
        include_full_results=request.include_full_results,
    )