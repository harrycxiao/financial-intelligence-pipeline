# src/analytics/derived_metrics/market_analysis.py

from datetime import date
import math
from typing import Optional

import pandas as pd

from src.database import query


def get_price_dataframe(
    ticker: str,
    as_of_date: Optional[date] = None,
) -> pd.DataFrame:
    """Load stored market data into a chronological DataFrame."""

    market_data = query.get_market_data(ticker)

    if not market_data:
        return pd.DataFrame()

    df = pd.DataFrame(market_data).copy()
    df["date"] = pd.to_datetime(df["date"])

    if as_of_date is not None:
        df = df.loc[df["date"] <= pd.to_datetime(as_of_date), :].copy()

    if df.empty:
        return df

    df = df.set_index("date")
    df = df.sort_index()
    df = df.reset_index()

    df["price"] = df["adjusted_close"].fillna(df["close"])

    return df


def calculate_returns_dataframe(
    ticker: str,
    as_of_date: Optional[date] = None,
) -> pd.DataFrame:
    """Calculate daily returns from adjusted close prices."""

    df = get_price_dataframe(ticker, as_of_date=as_of_date)

    if df.empty:
        return df

    df["daily_return"] = df["price"].pct_change()

    columns = ["date", "price", "daily_return", "volume"]
    return df.loc[:, columns].copy()


def calculate_cumulative_return(
    ticker: str,
    as_of_date: Optional[date] = None,
) -> Optional[float]:
    """Calculate total return over stored price history up to as_of_date."""

    df = get_price_dataframe(ticker, as_of_date=as_of_date)

    if df.empty or len(df) < 2:
        return None

    first_price = float(df["price"].iloc[0])
    last_price = float(df["price"].iloc[-1])

    if first_price == 0:
        return None

    return (last_price / first_price) - 1


def calculate_annualized_volatility(
    ticker: str,
    as_of_date: Optional[date] = None,
    trading_days: int = 252,
) -> Optional[float]:
    """Calculate annualized volatility from daily returns up to as_of_date."""

    returns = calculate_returns_dataframe(ticker, as_of_date=as_of_date)

    if returns.empty:
        return None

    daily_std = returns["daily_return"].std()

    if pd.isna(daily_std):
        return None

    return float(daily_std) * math.sqrt(trading_days)


def calculate_max_drawdown(
    ticker: str,
    as_of_date: Optional[date] = None,
) -> Optional[float]:
    """Calculate maximum drawdown from price history up to as_of_date."""

    df = get_price_dataframe(ticker, as_of_date=as_of_date)

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
    as_of_date: Optional[date] = None,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> Optional[float]:
    """Calculate annualized Sharpe ratio using daily returns up to as_of_date."""

    returns = calculate_returns_dataframe(ticker, as_of_date=as_of_date)

    if returns.empty:
        return None

    excess_daily_return = returns["daily_return"].dropna() - (risk_free_rate / trading_days)

    if excess_daily_return.empty:
        return None

    excess_std = excess_daily_return.std()

    if pd.isna(excess_std) or excess_std == 0:
        return None

    return float((excess_daily_return.mean() / excess_std) * math.sqrt(trading_days))


def calculate_beta(
    ticker: str,
    benchmark_ticker: str = "SPY",
    as_of_date: Optional[date] = None,
) -> Optional[float]:
    """Calculate beta versus a benchmark ticker using stored price data up to as_of_date."""

    stock_returns = calculate_returns_dataframe(ticker, as_of_date=as_of_date)
    benchmark_returns = calculate_returns_dataframe(benchmark_ticker, as_of_date=as_of_date)

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


def calculate_period_return(
    ticker: str,
    trading_days: int,
    as_of_date: Optional[date] = None,
) -> Optional[float]:
    """Calculate return over the most recent N trading days ending at as_of_date."""

    df = get_price_dataframe(ticker, as_of_date=as_of_date)

    if df.empty or len(df) <= trading_days:
        return None

    start_price = float(df["price"].iloc[-trading_days - 1])
    end_price = float(df["price"].iloc[-1])

    if start_price == 0:
        return None

    return (end_price / start_price) - 1


def calculate_market_summary(
    ticker: str,
    as_of_date: Optional[date] = None,
) -> dict:
    """Calculate core market behavior metrics for a ticker as of a date."""

    return {
        "ticker": ticker.upper().strip(),
        "as_of_date": as_of_date,
        "cumulative_return": calculate_cumulative_return(ticker, as_of_date=as_of_date),
        "one_month_return": calculate_period_return(ticker, 21, as_of_date=as_of_date),
        "three_month_return": calculate_period_return(ticker, 63, as_of_date=as_of_date),
        "six_month_return": calculate_period_return(ticker, 126, as_of_date=as_of_date),
        "one_year_return": calculate_period_return(ticker, 252, as_of_date=as_of_date),
        "annualized_volatility": calculate_annualized_volatility(ticker, as_of_date=as_of_date),
        "max_drawdown": calculate_max_drawdown(ticker, as_of_date=as_of_date),
        "sharpe_ratio": calculate_sharpe_ratio(ticker, as_of_date=as_of_date),
        "beta_vs_spy": calculate_beta(ticker, "SPY", as_of_date=as_of_date),
    }