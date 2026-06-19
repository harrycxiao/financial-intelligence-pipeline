# src/ingestion/sec_ingestion.py

from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup


SEC_HEADERS = {
    "User-Agent": "Harry Xiao harrycxiaon1@gmail.com"
}


DEFAULT_FORM_LIMITS = {
    "10-K": 3,
    "10-Q": 4,
    "8-K": 8,
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


def fetch_company_submissions(cik: str) -> dict:
    """Fetch SEC submissions metadata for a company."""

    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    response = requests.get(url, headers=SEC_HEADERS, timeout=30)
    response.raise_for_status()

    return response.json()


def build_filing_url(cik: str, accession_number: str, primary_document: str) -> str:
    """Build the SEC Archives URL for a filing's primary document."""

    cik_no_leading_zeros = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")

    return (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_no_leading_zeros}/{accession_no_dashes}/{primary_document}"
    )


def fetch_filing_text(filing_url: str) -> str:
    """Fetch and lightly clean the filing document text."""

    response = requests.get(filing_url, headers=SEC_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)

    return " ".join(text.split())


def extract_recent_filings(
    ticker: str,
    cik: str,
    submissions: dict,
    form_limits: dict[str, int],
) -> list[dict]:
    """Extract recent 10-K, 10-Q, and 8-K filing metadata from SEC submissions."""

    recent = submissions["filings"]["recent"]

    forms = recent["form"]
    filing_dates = recent["filingDate"]
    accession_numbers = recent["accessionNumber"]
    primary_documents = recent["primaryDocument"]

    counts = {form_type: 0 for form_type in form_limits}
    filings = []

    for form, filing_date, accession_number, primary_document in zip(
        forms,
        filing_dates,
        accession_numbers,
        primary_documents,
    ):
        if form not in form_limits:
            continue

        if counts[form] >= form_limits[form]:
            continue

        filing_url = build_filing_url(
            cik=cik,
            accession_number=accession_number,
            primary_document=primary_document,
        )

        raw_text = fetch_filing_text(filing_url)

        filings.append(
            {
                "ticker": ticker,
                "cik": cik,
                "filing_type": form,
                "filing_date": filing_date,
                "accession_number": accession_number,
                "filing_url": filing_url,
                "raw_text": raw_text,
                "summary": None,
            }
        )

        counts[form] += 1

        if all(counts[form_type] >= limit for form_type, limit in form_limits.items()):
            break

    return filings


def fetch_sec_filings(
    ticker: str,
    form_limits: Optional[dict[str, int]] = None,
) -> pd.DataFrame:
    """Fetch recent SEC filings for a ticker."""

    ticker = ticker.upper().strip()

    if form_limits is None:
        form_limits = DEFAULT_FORM_LIMITS

    cik = get_cik_for_ticker(ticker)

    if cik is None:
        raise ValueError(f"No CIK found for ticker: {ticker}")

    submissions = fetch_company_submissions(cik)

    filings = extract_recent_filings(
        ticker=ticker,
        cik=cik,
        submissions=submissions,
        form_limits=form_limits,
    )

    return pd.DataFrame(filings)


if __name__ == "__main__":
    stock = input("Enter stock ticker: ")
    df = fetch_sec_filings(stock)

    print(df[["ticker", "filing_type", "filing_date", "accession_number", "filing_url"]])
    print(f"Rows fetched: {len(df)}")
