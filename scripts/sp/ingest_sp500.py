# scripts/ingest_sp500.py

import time
from typing import Optional

import pandas as pd

from src.ingestion.company_ingestion import fetch_company_metadata
from src.ingestion.market_data_ingestion import fetch_market_data
from src.ingestion.financial_metrics_ingestion import fetch_financial_metrics

from src.database.store import (
    store_company,
    store_market_data,
    store_financial_metrics,
)


def fetch_sp500_tickers(limit: Optional[int] = None) -> list[str]:
    """
    Fetch the current S&P 500 ticker list from Wikipedia.

    Yahoo Finance uses BRK-B / BF-B format instead of BRK.B / BF.B.
    """

    import requests

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    constituents = tables[0]

    tickers = (
        constituents["Symbol"]
        .astype(str)
        .str.replace(".", "-", regex=False)
        .str.upper()
        .str.strip()
        .tolist()
    )

    if limit is not None:
        return tickers[:limit]

    return tickers


def ingest_one_ticker(
    ticker: str,
    market_period: str = "5y",
    market_interval: str = "1d",
    years_back: int = 5,
    include_quarterly: bool = True,
) -> dict:
    """Ingest company metadata, market data, and fundamentals for one ticker."""

    result = {
        "ticker": ticker,
        "company_stored": False,
        "market_rows": 0,
        "financial_rows": 0,
        "success": False,
        "error": None,
    }

    try:
        metadata = fetch_company_metadata(ticker)
        store_company(metadata)
        result["company_stored"] = True

        market_df = fetch_market_data(
            ticker=ticker,
            period=market_period,
            interval=market_interval,
        )
        store_market_data(ticker, market_df)
        result["market_rows"] = len(market_df)

        financial_df = fetch_financial_metrics(
            ticker=ticker,
            years_back=years_back,
            include_quarterly=include_quarterly,
        )
        store_financial_metrics(ticker, financial_df)
        result["financial_rows"] = len(financial_df)

        result["success"] = True

    except Exception as error:
        result["error"] = str(error)

    return result


def ingest_sp500_universe(
    limit: Optional[int] = None,
    sleep_seconds: float = 0.25,
    market_period: str = "5y",
    market_interval: str = "1d",
    years_back: int = 5,
    include_quarterly: bool = True,
    output_csv_path: str = "results/sp500_ingestion_results.csv",
) -> pd.DataFrame:
    """
    Ingest S&P 500 company metadata, market data, and financial metrics.

    This intentionally skips SEC filings text and news because the first
    quant/backtest pipeline only needs market data and fundamentals.
    """

    tickers = fetch_sp500_tickers(limit=limit)
    results = []

    print(f"Starting ingestion for {len(tickers)} tickers.")

    for index, ticker in enumerate(tickers, start=1):
        print(f"\n[{index}/{len(tickers)}] Ingesting {ticker}...")

        result = ingest_one_ticker(
            ticker=ticker,
            market_period=market_period,
            market_interval=market_interval,
            years_back=years_back,
            include_quarterly=include_quarterly,
        )

        results.append(result)

        if result["success"]:
            print(
                f"SUCCESS {ticker}: "
                f"market_rows={result['market_rows']}, "
                f"financial_rows={result['financial_rows']}"
            )
        else:
            print(f"FAILED {ticker}: {result['error']}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv_path, index=False)

    successful = int(results_df["success"].sum())
    failed = len(results_df) - successful

    print("\n--- Ingestion Complete ---")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Saved results to: {output_csv_path}")

    return results_df


if __name__ == "__main__":
    # For quick smoke test, use limit=10.
    # For full S&P 500 ingestion, set limit=None.
    ingest_sp500_universe(
        limit=None,
        sleep_seconds=0.25,
        market_period="5y",
        market_interval="1d",
        years_back=5,
        include_quarterly=True,
    )