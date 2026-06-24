# src/analytics/derived_metrics/market_analysis.py

import math
from typing import Optional

import pandas as pd

from src.database import query


def get_price_dataframe(ticker: str) -> pd.DataFrame:
    """Load stored market data into a chronological DataFrame."""

    market_data = query.get_market_data(ticker)

    if not market_data:
        return pd.DataFrame()

    df = pd.DataFrame(market_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["price"] = df["adjusted_close"].fillna(df["close"])

    return df


def calculate_returns_dataframe(ticker: str) -> pd.DataFrame:
    """Calculate daily returns from adjusted close prices."""

    df = get_price_dataframe(ticker)

    if df.empty:
        return df

    df["daily_return"] = df["price"].pct_change()

    columns = ["date", "price", "daily_return", "volume"]
    return df.loc[:, columns].copy()


def calculate_cumulative_return(ticker: str) -> Optional[float]:
    """Calculate total return over stored price history."""

    df = get_price_dataframe(ticker)

    if df.empty or len(df) < 2:
        return None

    first_price = float(df["price"].iloc[0])
    last_price = float(df["price"].iloc[-1])

    if first_price == 0:
        return None

    return (last_price / first_price) - 1


def calculate_annualized_volatility(
    ticker: str,
    trading_days: int = 252,
) -> Optional[float]:
    """Calculate annualized volatility from daily returns."""

    returns = calculate_returns_dataframe(ticker)

    if returns.empty:
        return None

    daily_std = returns["daily_return"].std()

    if pd.isna(daily_std):
        return None

    return float(daily_std) * math.sqrt(trading_days)


def calculate_max_drawdown(ticker: str) -> Optional[float]:
    """Calculate maximum drawdown from price history."""

    df = get_price_dataframe(ticker)

    if df.empty:
        return None

    cumulative_max = df["price"].cummax()
    drawdowns = (df["price"] - cumulative_max) / cumulative_max

    max_drawdown = drawdowns.min()

    if pd.isna(max_drawdown):
        return None

    return float(max_drawdown)


def calculate_sharpe_ratio(
    ticker: str,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> Optional[float]:
    """Calculate annualized Sharpe ratio using daily returns."""

    returns = calculate_returns_dataframe(ticker)

    if returns.empty:
        return None

    excess_daily_return = returns["daily_return"].dropna() - (risk_free_rate / trading_days)

    if excess_daily_return.empty:
        return None

    excess_std = excess_daily_return.std()

    if pd.isna(excess_std) or excess_std == 0:
        return None

    return float((excess_daily_return.mean() / excess_std) * math.sqrt(trading_days))


def calculate_beta(ticker: str, benchmark_ticker: str = "SPY") -> Optional[float]:
    """Calculate beta versus a benchmark ticker using stored price data."""

    stock_returns = calculate_returns_dataframe(ticker)
    benchmark_returns = calculate_returns_dataframe(benchmark_ticker)

    if stock_returns.empty or benchmark_returns.empty:
        return None

    merged = stock_returns[["date", "daily_return"]].merge(
        benchmark_returns[["date", "daily_return"]],
        on="date",
        suffixes=("_stock", "_benchmark"),
    ).dropna()

    if merged.empty:
        return None

    benchmark_variance = merged["daily_return_benchmark"].var()

    if pd.isna(benchmark_variance) or benchmark_variance == 0:
        return None

    covariance = merged["daily_return_stock"].cov(merged["daily_return_benchmark"])

    if pd.isna(covariance):
        return None

    return float(covariance / benchmark_variance)


def calculate_period_return(ticker: str, trading_days: int) -> Optional[float]:
    """Calculate return over the most recent N trading days."""

    df = get_price_dataframe(ticker)

    if df.empty or len(df) <= trading_days:
        return None

    start_price = float(df["price"].iloc[-trading_days - 1])
    end_price = float(df["price"].iloc[-1])

    if start_price == 0:
        return None

    return (end_price / start_price) - 1


def calculate_market_summary(ticker: str) -> dict:
    """Calculate core market behavior metrics for a ticker."""

    return {
        "ticker": ticker.upper().strip(),
        "cumulative_return": calculate_cumulative_return(ticker),
        "one_month_return": calculate_period_return(ticker, 21),
        "three_month_return": calculate_period_return(ticker, 63),
        "six_month_return": calculate_period_return(ticker, 126),
        "one_year_return": calculate_period_return(ticker, 252),
        "annualized_volatility": calculate_annualized_volatility(ticker),
        "max_drawdown": calculate_max_drawdown(ticker),
        "sharpe_ratio": calculate_sharpe_ratio(ticker),
        "beta_vs_spy": calculate_beta(ticker, "SPY"),
    }