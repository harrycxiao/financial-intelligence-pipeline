# src/analytics/research_models/factor_models.py

from datetime import date
from typing import Optional

import pandas as pd

from src.analytics.derived_metrics import (
    calculate_fundamental_summary,
    calculate_latest_technical_snapshot,
    calculate_market_summary,
)


FACTOR_WEIGHTS = {
    "value_score": 0.20,
    "quality_score": 0.20,
    "growth_score": 0.15,
    "momentum_score": 0.15,
    "financial_strength_score": 0.10,
    "risk_score": 0.10,
    "efficiency_score": 0.05,
    "technical_score": 0.05,
}


def clean_value(value) -> Optional[float]:
    """Convert pandas/numpy missing values into normal Python floats."""

    if value is None or pd.isna(value):
        return None

    return float(value)


def robust_score(
    series: pd.Series,
    higher_is_better: bool = True,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
) -> pd.Series:
    """
    Convert raw values into 0-100 scores using clipped min-max scaling.

    This keeps magnitude information while reducing outlier impact.
    """

    clean_series = pd.Series(
        pd.to_numeric(series, errors="coerce"),
        index=series.index,
    )

    if clean_series.dropna().empty:
        return pd.Series([None] * len(series), index=series.index)

    lower = clean_series.quantile(lower_quantile)
    upper = clean_series.quantile(upper_quantile)

    clipped = clean_series.clip(lower=lower, upper=upper)

    min_value = clipped.min()
    max_value = clipped.max()

    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series([50.0] * len(series), index=series.index)

    scores = ((clipped - min_value) / (max_value - min_value)) * 100

    if not higher_is_better:
        scores = 100 - scores

    return scores


def weighted_average_available_columns(df: pd.DataFrame, columns: dict) -> pd.Series:
    """
    Score selected columns and combine them into one weighted factor score.

    columns maps metric_name -> {"higher_is_better": bool, "weight": float}
    """

    scored_columns = []
    weights = []

    for column_name, config in columns.items():
        if column_name not in df.columns:
            continue

        scored = robust_score(
            df[column_name],
            higher_is_better=config["higher_is_better"],
        )

        scored_columns.append(scored)
        weights.append(config["weight"])

    if not scored_columns:
        return pd.Series([None] * len(df), index=df.index)

    score_df = pd.concat(scored_columns, axis=1)
    weight_series = pd.Series(weights, index=score_df.columns)

    weighted_scores = score_df.multiply(weight_series, axis=1)
    available_weights = score_df.notna().multiply(weight_series, axis=1)

    return weighted_scores.sum(axis=1) / available_weights.sum(axis=1)


def calculate_rsi_score(rsi: Optional[float]) -> Optional[float]:
    """
    Score RSI for medium-term momentum.

    Best zone is positive but not extremely overbought.
    """

    if rsi is None:
        return None

    if 50 <= rsi <= 70:
        return 100.0

    if 40 <= rsi < 50:
        return 70.0

    if 70 < rsi <= 80:
        return 60.0

    if 30 <= rsi < 40:
        return 40.0

    return 10.0


def build_factor_dataset(
    tickers: list,
    as_of_date: Optional[date] = None,
) -> pd.DataFrame:
    """Build one raw factor row per ticker."""

    rows = []

    for ticker in tickers:
        ticker = ticker.upper().strip()

        fundamental_summary = calculate_fundamental_summary(
            ticker,
            as_of_date=as_of_date,
        )
        latest_fundamentals = fundamental_summary.get("latest_metrics") or {}

        market_summary = calculate_market_summary(
            ticker,
            as_of_date=as_of_date,
        )
        technical_snapshot = calculate_latest_technical_snapshot(
            ticker,
            as_of_date=as_of_date,
        )

        price = clean_value(technical_snapshot.get("price"))
        sma_50 = clean_value(technical_snapshot.get("sma_50"))
        sma_200 = clean_value(technical_snapshot.get("sma_200"))
        macd = clean_value(technical_snapshot.get("macd"))
        macd_signal = clean_value(technical_snapshot.get("macd_signal"))

        row = {
            "ticker": ticker,

            # Value
            "earnings_yield": latest_fundamentals.get("earnings_yield"),
            "free_cash_flow_yield": latest_fundamentals.get("free_cash_flow_yield"),
            "sales_yield": latest_fundamentals.get("sales_yield"),
            "book_to_market": latest_fundamentals.get("book_to_market"),
            "ev_to_sales": latest_fundamentals.get("ev_to_sales"),
            "ev_to_operating_income": latest_fundamentals.get("ev_to_operating_income"),
            "ev_to_ebitda": latest_fundamentals.get("ev_to_ebitda"),
            "ev_to_free_cash_flow": latest_fundamentals.get("ev_to_free_cash_flow"),

            # Growth
            "revenue_growth": latest_fundamentals.get("revenue_growth"),
            "net_income_growth": latest_fundamentals.get("net_income_growth"),
            "free_cash_flow_growth": latest_fundamentals.get("free_cash_flow_growth"),
            "revenue_cagr": fundamental_summary.get("revenue_cagr"),
            "net_income_cagr": fundamental_summary.get("net_income_cagr"),
            "free_cash_flow_cagr": fundamental_summary.get("free_cash_flow_cagr"),

            # Quality
            "gross_margin": latest_fundamentals.get("gross_margin"),
            "operating_margin": latest_fundamentals.get("operating_margin"),
            "ebitda_margin": latest_fundamentals.get("ebitda_margin"),
            "net_margin": latest_fundamentals.get("net_margin"),
            "free_cash_flow_margin": latest_fundamentals.get("free_cash_flow_margin"),
            "return_on_assets": latest_fundamentals.get("return_on_assets"),
            "return_on_equity": latest_fundamentals.get("return_on_equity"),
            "return_on_invested_capital": latest_fundamentals.get(
                "return_on_invested_capital"
            ),
            "operating_cash_flow_to_net_income": latest_fundamentals.get(
                "operating_cash_flow_to_net_income"
            ),
            "free_cash_flow_to_net_income": latest_fundamentals.get(
                "free_cash_flow_to_net_income"
            ),

            # Financial strength
            "debt_to_assets": latest_fundamentals.get("debt_to_assets"),
            "debt_to_equity": latest_fundamentals.get("debt_to_equity"),
            "net_debt_to_equity": latest_fundamentals.get("net_debt_to_equity"),
            "liabilities_to_assets": latest_fundamentals.get("liabilities_to_assets"),
            "cash_to_debt": latest_fundamentals.get("cash_to_debt"),
            "current_ratio": latest_fundamentals.get("current_ratio"),
            "quick_ratio": latest_fundamentals.get("quick_ratio"),
            "interest_coverage": latest_fundamentals.get("interest_coverage"),

            # Efficiency
            "asset_turnover": latest_fundamentals.get("asset_turnover"),
            "r_and_d_intensity": latest_fundamentals.get("r_and_d_intensity"),
            "sga_intensity": latest_fundamentals.get("sga_intensity"),
            "capex_to_revenue": latest_fundamentals.get("capex_to_revenue"),

            # Momentum
            "cumulative_return": market_summary.get("cumulative_return"),
            "one_month_return": market_summary.get("one_month_return"),
            "three_month_return": market_summary.get("three_month_return"),
            "six_month_return": market_summary.get("six_month_return"),
            "one_year_return": market_summary.get("one_year_return"),
            "sharpe_ratio": market_summary.get("sharpe_ratio"),

            # Risk
            "annualized_volatility": market_summary.get("annualized_volatility"),
            "max_drawdown": market_summary.get("max_drawdown"),
            "beta_vs_spy": market_summary.get("beta_vs_spy"),

            # Technicals
            "price_vs_sma_50": (
                (price / sma_50) - 1
                if price is not None and sma_50 is not None and sma_50 != 0
                else None
            ),
            "price_vs_sma_200": (
                (price / sma_200) - 1
                if price is not None and sma_200 is not None and sma_200 != 0
                else None
            ),
            "sma_50_vs_sma_200": (
                (sma_50 / sma_200) - 1
                if sma_50 is not None and sma_200 is not None and sma_200 != 0
                else None
            ),
            "macd_spread": (
                (macd - macd_signal) / price
                if macd is not None
                and macd_signal is not None
                and price is not None
                and price != 0
                else None
            ),
            "rsi_score": calculate_rsi_score(clean_value(technical_snapshot.get("rsi_14"))),
            "volume_ratio": technical_snapshot.get("volume_ratio"),
        }

        rows.append(row)

    return pd.DataFrame(rows)


def calculate_factor_scores(
    tickers: list,
    as_of_date: Optional[date] = None,
) -> pd.DataFrame:
    """Calculate cross-sectional factor scores for a ticker universe."""

    df = build_factor_dataset(
        tickers,
        as_of_date=as_of_date,
    )

    if df.empty:
        return df

    df["value_score"] = weighted_average_available_columns(
        df,
        {
            "earnings_yield": {"higher_is_better": True, "weight": 0.20},
            "free_cash_flow_yield": {"higher_is_better": True, "weight": 0.25},
            "sales_yield": {"higher_is_better": True, "weight": 0.10},
            "book_to_market": {"higher_is_better": True, "weight": 0.10},
            "ev_to_sales": {"higher_is_better": False, "weight": 0.10},
            "ev_to_operating_income": {"higher_is_better": False, "weight": 0.10},
            "ev_to_ebitda": {"higher_is_better": False, "weight": 0.10},
            "ev_to_free_cash_flow": {"higher_is_better": False, "weight": 0.05},
        },
    )

    df["growth_score"] = weighted_average_available_columns(
        df,
        {
            "revenue_growth": {"higher_is_better": True, "weight": 0.20},
            "net_income_growth": {"higher_is_better": True, "weight": 0.20},
            "free_cash_flow_growth": {"higher_is_better": True, "weight": 0.20},
            "revenue_cagr": {"higher_is_better": True, "weight": 0.15},
            "net_income_cagr": {"higher_is_better": True, "weight": 0.15},
            "free_cash_flow_cagr": {"higher_is_better": True, "weight": 0.10},
        },
    )

    df["quality_score"] = weighted_average_available_columns(
        df,
        {
            "gross_margin": {"higher_is_better": True, "weight": 0.10},
            "operating_margin": {"higher_is_better": True, "weight": 0.15},
            "ebitda_margin": {"higher_is_better": True, "weight": 0.10},
            "net_margin": {"higher_is_better": True, "weight": 0.10},
            "free_cash_flow_margin": {"higher_is_better": True, "weight": 0.15},
            "return_on_assets": {"higher_is_better": True, "weight": 0.10},
            "return_on_equity": {"higher_is_better": True, "weight": 0.10},
            "return_on_invested_capital": {"higher_is_better": True, "weight": 0.15},
            "operating_cash_flow_to_net_income": {"higher_is_better": True, "weight": 0.05},
        },
    )

    df["financial_strength_score"] = weighted_average_available_columns(
        df,
        {
            "debt_to_assets": {"higher_is_better": False, "weight": 0.20},
            "debt_to_equity": {"higher_is_better": False, "weight": 0.15},
            "net_debt_to_equity": {"higher_is_better": False, "weight": 0.20},
            "liabilities_to_assets": {"higher_is_better": False, "weight": 0.15},
            "cash_to_debt": {"higher_is_better": True, "weight": 0.10},
            "current_ratio": {"higher_is_better": True, "weight": 0.10},
            "quick_ratio": {"higher_is_better": True, "weight": 0.05},
            "interest_coverage": {"higher_is_better": True, "weight": 0.05},
        },
    )

    df["efficiency_score"] = weighted_average_available_columns(
        df,
        {
            "asset_turnover": {"higher_is_better": True, "weight": 0.40},
            "r_and_d_intensity": {"higher_is_better": True, "weight": 0.25},
            "sga_intensity": {"higher_is_better": False, "weight": 0.20},
            "capex_to_revenue": {"higher_is_better": False, "weight": 0.15},
        },
    )

    df["momentum_score"] = weighted_average_available_columns(
        df,
        {
            "one_month_return": {"higher_is_better": True, "weight": 0.15},
            "three_month_return": {"higher_is_better": True, "weight": 0.25},
            "six_month_return": {"higher_is_better": True, "weight": 0.25},
            "one_year_return": {"higher_is_better": True, "weight": 0.20},
            "sharpe_ratio": {"higher_is_better": True, "weight": 0.15},
        },
    )

    df["risk_score"] = weighted_average_available_columns(
        df,
        {
            "annualized_volatility": {"higher_is_better": False, "weight": 0.40},
            "max_drawdown": {"higher_is_better": True, "weight": 0.35},
            "beta_vs_spy": {"higher_is_better": False, "weight": 0.25},
        },
    )

    df["technical_score"] = weighted_average_available_columns(
        df,
        {
            "price_vs_sma_50": {"higher_is_better": True, "weight": 0.22},
            "price_vs_sma_200": {"higher_is_better": True, "weight": 0.22},
            "sma_50_vs_sma_200": {"higher_is_better": True, "weight": 0.22},
            "macd_spread": {"higher_is_better": True, "weight": 0.14},
            "rsi_score": {"higher_is_better": True, "weight": 0.10},
            "volume_ratio": {"higher_is_better": True, "weight": 0.10},
        },
    )

    df["overall_score"] = 0.0
    total_weight = 0.0

    for factor_name, weight in FACTOR_WEIGHTS.items():
        if factor_name in df.columns:
            df["overall_score"] += df[factor_name].fillna(0) * weight
            total_weight += weight

    if total_weight > 0:
        df["overall_score"] = df["overall_score"] / total_weight

    return df.sort_values("overall_score", ascending=False).reset_index(drop=True)


def rank_companies(
    tickers: list,
    as_of_date: Optional[date] = None,
) -> list:

    """Return ranked factor scores as dictionaries."""

    scores = calculate_factor_scores(
        tickers,
        as_of_date=as_of_date,
    )

    if scores.empty:
        return []

    return scores.to_dict(orient="records")


def get_company_factor_profile(
    ticker: str,
    peer_tickers: list,
    as_of_date: Optional[date] = None,
) -> dict:
    """Return one company's factor profile relative to a peer universe."""

    ticker = ticker.upper().strip()
    tickers = list(set([ticker] + [peer.upper().strip() for peer in peer_tickers]))

    scores = calculate_factor_scores(
        tickers,
        as_of_date=as_of_date,
    )

    if scores.empty:
        return {}

    company_row = scores[scores["ticker"] == ticker]

    if company_row.empty:
        return {}

    return company_row.iloc[0].to_dict()