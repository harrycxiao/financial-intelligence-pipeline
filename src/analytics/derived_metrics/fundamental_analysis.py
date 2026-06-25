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


def get_latest_market_cap(ticker: str) -> Optional[float]:
    """Calculate latest market cap from latest price and shares outstanding."""

    latest_price = query.get_latest_market_price(ticker)

    if latest_price is None:
        return None

    price = to_float(
        latest_price.get("adjusted_close")
        if latest_price.get("adjusted_close") is not None
        else latest_price.get("close")
    )
    shares_outstanding = to_float(latest_price.get("shares_outstanding"))

    if price is None or shares_outstanding is None:
        return None

    return price * shares_outstanding


def calculate_fundamental_metrics(ticker: str) -> list:
    """Calculate core business-quality and valuation metrics."""

    df = get_financial_metrics_dataframe(ticker)
    market_cap = get_latest_market_cap(ticker)

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
        current_assets = to_float(row.get("current_assets"))
        current_liabilities = to_float(row.get("current_liabilities"))
        inventory = to_float(row.get("inventory"))
        cash = to_float(row.get("cash_and_equivalents"))
        total_debt = to_float(row.get("total_debt"))

        operating_cash_flow = to_float(row.get("operating_cash_flow"))
        capital_expenditures = to_float(row.get("capital_expenditures"))
        free_cash_flow = to_float(row.get("free_cash_flow"))

        depreciation_and_amortization = to_float(row.get("depreciation_and_amortization"))
        r_and_d_expense = to_float(row.get("r_and_d_expense"))
        sga_expense = to_float(row.get("sga_expense"))
        interest_expense = to_float(row.get("interest_expense"))
        income_tax_expense = to_float(row.get("income_tax_expense"))
        dividends_paid = to_float(row.get("dividends_paid"))

        weighted_average_shares = to_float(row.get("weighted_average_shares"))
        weighted_average_diluted_shares = to_float(row.get("weighted_average_diluted_shares"))

        previous_revenue = to_float(previous.get("revenue")) if previous is not None else None
        previous_net_income = to_float(previous.get("net_income")) if previous is not None else None
        previous_free_cash_flow = to_float(previous.get("free_cash_flow")) if previous is not None else None

        book_equity = (
            total_assets - total_liabilities
            if total_assets is not None and total_liabilities is not None
            else None
        )

        net_debt = (
            total_debt - cash
            if total_debt is not None and cash is not None
            else None
        )

        invested_capital = (
            total_debt + book_equity
            if total_debt is not None and book_equity is not None
            else None
        )

        ebitda = (
            operating_income + depreciation_and_amortization
            if operating_income is not None and depreciation_and_amortization is not None
            else None
        )

        enterprise_value = (
            market_cap + total_debt - cash
            if market_cap is not None and total_debt is not None and cash is not None
            else None
        )

        pretax_income = (
            net_income + income_tax_expense
            if net_income is not None and income_tax_expense is not None
            else None
        )

        metrics = {
            "ticker": ticker.upper().strip(),
            "period_end_date": row.get("period_end_date"),
            "fiscal_year": row.get("fiscal_year"),
            "fiscal_period": row.get("fiscal_period"),

            # Balance sheet / valuation base values
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "book_equity": book_equity,
            "net_debt": net_debt,
            "invested_capital": invested_capital,
            "ebitda": ebitda,

            # Growth
            "revenue_growth": calculate_growth(revenue, previous_revenue),
            "net_income_growth": calculate_growth(net_income, previous_net_income),
            "free_cash_flow_growth": calculate_growth(free_cash_flow, previous_free_cash_flow),

            # Profitability / margins
            "gross_margin": safe_divide(gross_profit, revenue),
            "operating_margin": safe_divide(operating_income, revenue),
            "ebitda_margin": safe_divide(ebitda, revenue),
            "net_margin": safe_divide(net_income, revenue),
            "free_cash_flow_margin": safe_divide(free_cash_flow, revenue),

            # Returns on capital
            "return_on_assets": safe_divide(net_income, total_assets),
            "return_on_equity": safe_divide(net_income, book_equity),
            "return_on_invested_capital": safe_divide(operating_income, invested_capital),

            # Leverage / liquidity
            "debt_to_assets": safe_divide(total_debt, total_assets),
            "debt_to_equity": safe_divide(total_debt, book_equity),
            "net_debt_to_equity": safe_divide(net_debt, book_equity),
            "liabilities_to_assets": safe_divide(total_liabilities, total_assets),
            "cash_to_debt": safe_divide(cash, total_debt),
            "current_ratio": safe_divide(current_assets, current_liabilities),
            "quick_ratio": safe_divide(
                current_assets - inventory
                if current_assets is not None and inventory is not None
                else None,
                current_liabilities,
            ),

            # Efficiency
            "asset_turnover": safe_divide(revenue, total_assets),
            "r_and_d_intensity": safe_divide(r_and_d_expense, revenue),
            "sga_intensity": safe_divide(sga_expense, revenue),
            "capex_to_revenue": safe_divide(abs(capital_expenditures) if capital_expenditures is not None else None, revenue),

            # Cash flow quality
            "operating_cash_flow_to_net_income": safe_divide(operating_cash_flow, net_income),
            "free_cash_flow_to_net_income": safe_divide(free_cash_flow, net_income),
            "dividend_payout_ratio": safe_divide(abs(dividends_paid) if dividends_paid is not None else None, net_income),

            # Coverage / tax
            "interest_coverage": safe_divide(operating_income, interest_expense),
            "effective_tax_rate": safe_divide(income_tax_expense, pretax_income),

            # Per-share metrics
            "basic_eps": safe_divide(net_income, weighted_average_shares),
            "diluted_eps": safe_divide(net_income, weighted_average_diluted_shares),
            "free_cash_flow_per_share": safe_divide(free_cash_flow, weighted_average_diluted_shares),

            # Valuation ratios
            "earnings_yield": safe_divide(net_income, market_cap),
            "free_cash_flow_yield": safe_divide(free_cash_flow, market_cap),
            "sales_yield": safe_divide(revenue, market_cap),
            "book_to_market": safe_divide(book_equity, market_cap),
            "price_to_book": safe_divide(market_cap, book_equity),
            "ev_to_sales": safe_divide(enterprise_value, revenue),
            "ev_to_operating_income": safe_divide(enterprise_value, operating_income),
            "ev_to_ebitda": safe_divide(enterprise_value, ebitda),
            "ev_to_free_cash_flow": safe_divide(enterprise_value, free_cash_flow),
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