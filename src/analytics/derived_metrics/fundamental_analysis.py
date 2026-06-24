# src/analytics/derived_metrics/fundamental_analysis.py

from typing import Optional

import pandas as pd

from src.database import query


def to_float(value) -> Optional[float]:
    """Convert pandas/numpy values into normal Python floats."""

    if value is None or pd.isna(value):
        return None

    return float(value)


def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safely divide two numbers."""

    if numerator is None or denominator is None or denominator == 0:
        return None

    return numerator / denominator


def calculate_growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Calculate period-over-period growth."""

    if current is None or previous is None or previous == 0:
        return None

    return (current - previous) / abs(previous)


def calculate_cagr(
    start_value: Optional[float],
    end_value: Optional[float],
    periods: int,
) -> Optional[float]:
    """Calculate compound annual growth rate."""

    if start_value is None or end_value is None or start_value <= 0 or periods <= 0:
        return None

    return (end_value / start_value) ** (1 / periods) - 1


def get_financial_metrics_dataframe(ticker: str) -> pd.DataFrame:
    """Load stored financial metrics into a chronological DataFrame."""

    financials = query.get_financial_metrics(ticker)

    if not financials:
        return pd.DataFrame()

    df = pd.DataFrame(financials)
    df["period_end_date"] = pd.to_datetime(df["period_end_date"])
    df = df.sort_values("period_end_date").reset_index(drop=True)

    return df


def calculate_fundamental_metrics(ticker: str) -> list:
    """Calculate core business-quality metrics from financial statements."""

    df = get_financial_metrics_dataframe(ticker)

    if df.empty:
        return []

    rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        previous = df.iloc[i - 1] if i > 0 else None

        revenue = to_float(row.get("revenue"))
        net_income = to_float(row.get("net_income"))
        operating_income = to_float(row.get("operating_income"))
        gross_profit = to_float(row.get("gross_profit"))
        total_assets = to_float(row.get("total_assets"))
        total_liabilities = to_float(row.get("total_liabilities"))
        cash = to_float(row.get("cash_and_equivalents"))
        total_debt = to_float(row.get("total_debt"))
        operating_cash_flow = to_float(row.get("operating_cash_flow"))
        free_cash_flow = to_float(row.get("free_cash_flow"))

        previous_revenue = to_float(previous.get("revenue")) if previous is not None else None
        previous_net_income = to_float(previous.get("net_income")) if previous is not None else None
        previous_free_cash_flow = to_float(previous.get("free_cash_flow")) if previous is not None else None

        equity = (
            total_assets - total_liabilities
            if total_assets is not None and total_liabilities is not None
            else None
        )

        metrics = {
            "ticker": ticker.upper().strip(),
            "period_end_date": row.get("period_end_date"),
            "fiscal_year": row.get("fiscal_year"),
            "fiscal_period": row.get("fiscal_period"),

            "revenue_growth": calculate_growth(revenue, previous_revenue),
            "net_income_growth": calculate_growth(net_income, previous_net_income),
            "free_cash_flow_growth": calculate_growth(free_cash_flow, previous_free_cash_flow),

            "gross_margin": safe_divide(gross_profit, revenue),
            "operating_margin": safe_divide(operating_income, revenue),
            "net_margin": safe_divide(net_income, revenue),
            "free_cash_flow_margin": safe_divide(free_cash_flow, revenue),

            "return_on_assets": safe_divide(net_income, total_assets),
            "return_on_equity": safe_divide(net_income, equity),

            "debt_to_assets": safe_divide(total_debt, total_assets),
            "debt_to_equity": safe_divide(total_debt, equity),
            "liabilities_to_assets": safe_divide(total_liabilities, total_assets),
            "cash_to_debt": safe_divide(cash, total_debt),

            "asset_turnover": safe_divide(revenue, total_assets),

            "operating_cash_flow_to_net_income": safe_divide(operating_cash_flow, net_income),
            "free_cash_flow_to_net_income": safe_divide(free_cash_flow, net_income),
        }

        rows.append(metrics)

    return list(reversed(rows))


def calculate_fundamental_summary(ticker: str) -> dict:
    """Calculate latest metrics plus multi-year growth summaries."""

    df = get_financial_metrics_dataframe(ticker)

    if df.empty:
        return {"ticker": ticker.upper().strip(), "metrics": []}

    metrics = calculate_fundamental_metrics(ticker)
    latest = metrics[0] if metrics else None

    first = df.iloc[0]
    last = df.iloc[-1]
    periods = len(df) - 1

    return {
        "ticker": ticker.upper().strip(),
        "latest_metrics": latest,
        "revenue_cagr": calculate_cagr(
            to_float(first.get("revenue")),
            to_float(last.get("revenue")),
            periods,
        ),
        "net_income_cagr": calculate_cagr(
            to_float(first.get("net_income")),
            to_float(last.get("net_income")),
            periods,
        ),
        "free_cash_flow_cagr": calculate_cagr(
            to_float(first.get("free_cash_flow")),
            to_float(last.get("free_cash_flow")),
            periods,
        ),
        "periods_used": len(df),
    }