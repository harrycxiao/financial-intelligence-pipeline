# src/ingestion/financial_metrics_ingestion.py

from typing import Optional

import pandas as pd
import requests


SEC_HEADERS = {
    "User-Agent": "Harry Xiao harrycxiaon1@gmail.com"
}


US_GAAP_TAGS = {
    "revenue": [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
    ],
    "net_income": ["NetIncomeLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashAndCashEquivalentsAndShortTermInvestments",
    ],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
}

DEBT_TAGS = [
    "ShortTermBorrowings",
    "CommercialPaper",
    "LongTermDebtCurrent",
    "LongTermDebtNoncurrent",
    "LongTermDebtAndFinanceLeaseObligationsCurrent",
    "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
]


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

def get_latest_fact(
    company_facts: dict,
    tag: str,
    fiscal_year: int,
    fiscal_period: str,
    period_end_date: str,
) -> Optional[dict]:
    """
    Find the latest filed SEC fact matching one exact fiscal period.

    Matching period_end_date is important because SEC companyfacts can include
    comparative prior-year facts inside newer filings.
    """

    facts = extract_usd_facts(company_facts, tag)

    candidates = [
        fact
        for fact in facts
        if (
            fact.get("fy") == fiscal_year
            and fact.get("fp") == fiscal_period
            and fact.get("end") == period_end_date
        )
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda fact: fact.get("filed", ""))

def get_latest_fact_value(
    company_facts: dict,
    possible_tags: list[str],
    fiscal_year: int,
    fiscal_period: str,
    period_end_date: str,
) -> Optional[float]:
    """
    Try multiple US-GAAP tags and return the first matching value.

    Different companies sometimes use different tags for the same concept.
    """

    for tag in possible_tags:
        fact = get_latest_fact(
            company_facts=company_facts,
            tag=tag,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            period_end_date=period_end_date,
        )

        if fact is not None and fact.get("val") is not None:
            return float(fact["val"])

    return None

def get_total_debt(
    company_facts: dict,
    fiscal_year: int,
    fiscal_period: str,
    period_end_date: str,
) -> Optional[float]:
    """
    Compute total debt by summing available current and noncurrent debt tags.
    """

    total_debt = 0.0
    found_any_debt = False

    for tag in DEBT_TAGS:
        fact = get_latest_fact(
            company_facts=company_facts,
            tag=tag,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            period_end_date=period_end_date,
        )

        if fact is not None and fact.get("val") is not None:
            total_debt += float(fact["val"])
            found_any_debt = True

    return total_debt if found_any_debt else None

def get_reporting_periods(company_facts: dict, years_back: int = 5) -> list[dict]:
    """
    Find recent annual reporting periods and remove SEC comparative duplicates.
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

    unique_periods = {}

    for period in periods:
        key = (
            period["fiscal_period"],
            period["period_end_date"],
        )

        if key not in unique_periods:
            unique_periods[key] = period
            continue

        existing = unique_periods[key]
        end_year = int(period["period_end_date"][:4])

        # Prefer the fiscal year that matches the period end year.
        if period["fiscal_year"] == end_year and existing["fiscal_year"] != end_year:
            unique_periods[key] = period

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
        period_end_date = period["period_end_date"]

        row = {
            "ticker": ticker,
            "cik": cik,
            "period_end_date": period_end_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
        }

        for metric_name, possible_tags in US_GAAP_TAGS.items():
            row[metric_name] = get_latest_fact_value(
                company_facts=company_facts,
                possible_tags=possible_tags,
                fiscal_year=fiscal_year,
                fiscal_period=fiscal_period,
                period_end_date=period_end_date,
            )

        row["total_debt"] = get_total_debt(
            company_facts=company_facts,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            period_end_date=period_end_date,
        )

        operating_cash_flow = row.get("operating_cash_flow")
        capital_expenditures = row.get("capital_expenditures")

        if operating_cash_flow is not None and capital_expenditures is not None:
            row["free_cash_flow"] = operating_cash_flow - abs(capital_expenditures)
        else:
            row["free_cash_flow"] = None

        row.pop("capital_expenditures", None)

        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    stock = input("Enter stock ticker: ")
    df = fetch_financial_metrics(stock)

    print(df)
    print(f"Rows fetched: {len(df)}")