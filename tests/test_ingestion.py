from src.ingestion.company_ingestion import fetch_company_metadata
from src.ingestion.market_data_ingestion import fetch_market_data
from src.ingestion.financial_metrics_ingestion import fetch_financial_metrics
from src.ingestion.sec_ingestion import fetch_sec_filings

from src.database.store import (
    store_company,
    store_market_data,
    store_financial_metrics,
    store_sec_filings,
)


TEST_TICKER = "AAPL"


# ---------------------------------------------------------------------
# Company ingestion + storage test
# ---------------------------------------------------------------------


def test_company_ingestion_and_storage() -> None:
    metadata = fetch_company_metadata(TEST_TICKER)
    company = store_company(metadata)

    print("Company stored:")
    print(company.id)
    print(company.ticker)
    print(company.name)
    print(company.exchange)


# ---------------------------------------------------------------------
# Market data ingestion + storage test
# ---------------------------------------------------------------------


def test_market_data_ingestion_and_storage() -> None:
    metadata = fetch_company_metadata(TEST_TICKER)
    store_company(metadata)

    df = fetch_market_data(TEST_TICKER)
    store_market_data(TEST_TICKER, df)

    print("Market data stored:")
    print(f"Ticker: {TEST_TICKER}")
    print(f"Rows fetched: {len(df)}")


# ---------------------------------------------------------------------
# Financial metrics ingestion + storage test
# ---------------------------------------------------------------------


def test_financial_metrics_ingestion_and_storage() -> None:
    metadata = fetch_company_metadata(TEST_TICKER)
    store_company(metadata)

    df = fetch_financial_metrics(TEST_TICKER)
    store_financial_metrics(TEST_TICKER, df)

    print("Financial metrics stored:")
    print(f"Ticker: {TEST_TICKER}")
    print(f"Rows fetched: {len(df)}")
    print(df)


# ---------------------------------------------------------------------
# SEC filings ingestion + storage test
# ---------------------------------------------------------------------


def test_sec_filings_ingestion_and_storage() -> None:
    metadata = fetch_company_metadata(TEST_TICKER)
    store_company(metadata)

    df = fetch_sec_filings(TEST_TICKER)
    store_sec_filings(TEST_TICKER, df)

    print("SEC filings stored:")
    print(f"Ticker: {TEST_TICKER}")
    print(f"Rows fetched: {len(df)}")
    print(df[["ticker", "filing_type", "filing_date", "accession_number", "filing_url"]])


if __name__ == "__main__":
    test_company_ingestion_and_storage()
    test_market_data_ingestion_and_storage()
    test_financial_metrics_ingestion_and_storage()
    test_sec_filings_ingestion_and_storage()