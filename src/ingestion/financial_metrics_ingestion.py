# src/ingestion/financial_metrics_ingestion.py

from typing import Optional

import pandas as pd
import requests


SEC_HEADERS = {
    "User-Agent": "Harry Xiao harrycxiaon1@gmail.com"
}


US_GAAP_TAGS = {
    "revenue": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "net_income": ["NetIncomeLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "total_debt": ["LongTermDebtAndFinanceLeaseObligationsCurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "free_cash_flow": ["FreeCashFlow"],
}


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """Look up a company's CIK from the SEC ticker mapping file."""

    ticker = ticker.upper().strip()

    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=SEC_HEADERS, timeout=30)
    response.raise_for_status()

    companies = response.json()

    for company in companies.values():
        if company["ticker"].upper() == ticker:
            return str(company["cik_str"]).zfill(10)

    return None


def fetch_company_facts(cik: str) -> dict:
    """Fetch raw SEC companyfacts JSON for a company CIK."""

    cik = cik.zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(url, headers=SEC_HEADERS, timeout=30)
    response.raise_for_status()

    return response.json()


def extract_usd_facts(company_facts: dict, us_gaap_tag: str) -> list[dict]:
    """Extract USD facts for one US-GAAP tag from SEC companyfacts."""

    facts = (
        company_facts
        .get("facts", {})
        .get("us-gaap", {})
        .get(us_gaap_tag, {})
        .get("units", {})
        .get("USD", [])
    )

    return facts


def get_latest_fact_value(company_facts: dict, possible_tags: list[str], fiscal_year: int, fiscal_period: str) -> Optional[float]:
    """
    Find the latest filed USD value for a given fiscal year and fiscal period.

    SEC companies sometimes use different US-GAAP tags for similar concepts,
    so possible_tags lets us try multiple tags.
    """

    candidates = []

    for tag in possible_tags:
        facts = extract_usd_facts(company_facts, tag)

        for fact in facts:
            if fact.get("fy") == fiscal_year and fact.get("fp") == fiscal_period:
                candidates.append(fact)

    if not candidates:
        return None

    latest_fact = max(candidates, key=lambda fact: fact.get("filed", ""))

    return float(latest_fact["val"]) if latest_fact.get("val") is not None else None


def get_reporting_periods(company_facts: dict, years_back: int = 5) -> list[dict]:
    """
    Find recent annual reporting periods from the revenue facts.

    This uses revenue-like tags as the anchor because most operating companies
    report revenue every fiscal year.
    """

    periods = []

    for tag in US_GAAP_TAGS["revenue"]:
        facts = extract_usd_facts(company_facts, tag)

        for fact in facts:
            if fact.get("fp") == "FY" and fact.get("fy") is not None and fact.get("end") is not None:
                periods.append(
                    {
                        "fiscal_year": fact["fy"],
                        "fiscal_period": fact["fp"],
                        "period_end_date": fact["end"],
                        "filed": fact.get("filed", ""),
                    }
                )

    unique_periods = {
        (period["fiscal_year"], period["fiscal_period"], period["period_end_date"]): period
        for period in periods
    }

    sorted_periods = sorted(
        unique_periods.values(),
        key=lambda period: period["period_end_date"],
        reverse=True,
    )

    return sorted_periods[:years_back]


def fetch_financial_metrics(ticker: str, years_back: int = 5) -> pd.DataFrame:
    """
    Fetch recent annual financial metrics from SEC companyfacts.

    Returns one row per fiscal year.
    """

    ticker = ticker.upper().strip()

    cik = get_cik_for_ticker(ticker)

    if cik is None:
        raise ValueError(f"No CIK found for ticker: {ticker}")

    company_facts = fetch_company_facts(cik)
    periods = get_reporting_periods(company_facts, years_back=years_back)

    rows = []

    for period in periods:
        fiscal_year = period["fiscal_year"]
        fiscal_period = period["fiscal_period"]

        row = {
            "ticker": ticker,
            "cik": cik,
            "period_end_date": period["period_end_date"],
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
        }

        for metric_name, possible_tags in US_GAAP_TAGS.items():
            row[metric_name] = get_latest_fact_value(
                company_facts=company_facts,
                possible_tags=possible_tags,
                fiscal_year=fiscal_year,
                fiscal_period=fiscal_period,
            )

        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    stock = input("Enter stock ticker: ")
    df = fetch_financial_metrics(stock)

    print(df)
    print(f"Rows fetched: {len(df)}")