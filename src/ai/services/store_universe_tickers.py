# src/ai/services/store_universe_tickers.py

from pathlib import Path
from typing import Optional
import time

import pandas as pd

from src.database.connection import SessionLocal
from src.database.models import Company, MarketPrice, FinancialMetric

from src.ingestion.company_ingestion import fetch_company_metadata
from src.ingestion.market_data_ingestion import fetch_market_data
from src.ingestion.financial_metrics_ingestion import fetch_financial_metrics

from src.database.store import (
    store_company,
    store_market_data,
    store_financial_metrics,
)


RATE_LIMIT_KEYWORDS = [
    "too many requests",
    "rate limited",
    "rate limit",
    "429",
    "temporarily unavailable",
    "connection aborted",
    "connection reset",
    "remote end closed",
    "timed out",
    "timeout",
    "dns",
    "name resolution",
    "failed to establish",
]


def is_rate_limit_like_error(error_message: str) -> bool:
    lower_error = str(error_message).lower()
    return any(keyword in lower_error for keyword in RATE_LIMIT_KEYWORDS)


def fetch_us_universe_tickers(
    limit: Optional[int] = None,
    eligible_csv_path: str = "results/us_universe_eligible_tickers.csv",
) -> list[str]:
    path = Path(eligible_csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Could not find eligible ticker file: {eligible_csv_path}. "
            "Run scripts/filter_us_universe.py first."
        )

    df = pd.read_csv(path)

    if "ticker" not in df.columns:
        raise ValueError(f"{eligible_csv_path} must contain a 'ticker' column.")

    tickers = (
        df["ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
        .drop_duplicates()
        .tolist()
    )

    if limit is not None:
        return tickers[:limit]

    return tickers


def get_existing_storage_status(ticker: str) -> Optional[dict]:
    session = SessionLocal()

    try:
        ticker = ticker.upper().strip()

        company = session.query(Company).filter(Company.ticker == ticker).first()

        if company is None:
            return None

        market_rows = (
            session.query(MarketPrice)
            .filter(MarketPrice.company_id == company.id)
            .count()
        )

        financial_rows = (
            session.query(FinancialMetric)
            .filter(FinancialMetric.company_id == company.id)
            .count()
        )

        return {
            "ticker": ticker,
            "company_stored": True,
            "market_rows": market_rows,
            "financial_rows": financial_rows,
        }

    finally:
        session.close()


def ingest_one_ticker(
    ticker: str,
    market_period: str = "20y",
    market_interval: str = "1d",
    years_back: int = 20,
    include_quarterly: bool = True,
    force_refresh: bool = True,
    max_retries: int = 3,
    retry_sleep_seconds: float = 10.0,
    cooldown_seconds: float = 3600.0,
) -> dict:
    ticker = ticker.upper().strip()

    existing_status = get_existing_storage_status(ticker)

    if (
        not force_refresh
        and existing_status is not None
        and existing_status["market_rows"] > 0
        and existing_status["financial_rows"] > 0
    ):
        return {
            "ticker": ticker,
            "company_stored": True,
            "market_rows": existing_status["market_rows"],
            "financial_rows": existing_status["financial_rows"],
            "success": True,
            "error": None,
            "skipped_existing": True,
        }

    attempt = 1

    result = {
        "ticker": ticker,
        "company_stored": False,
        "market_rows": 0,
        "financial_rows": 0,
        "success": False,
        "error": None,
        "skipped_existing": False,
    }

    while attempt <= max_retries:
        result = {
            "ticker": ticker,
            "company_stored": False,
            "market_rows": 0,
            "financial_rows": 0,
            "success": False,
            "error": None,
            "skipped_existing": False,
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
            return result

        except Exception as error:
            error_message = str(error)
            result["error"] = error_message

            is_database_error = (
                "psycopg2" in error_message.lower()
                or "sqlalchemy" in error_message.lower()
                or "numericvalueoutofrange" in error_message.lower()
                or "integer out of range" in error_message.lower()
            )

            if is_rate_limit_like_error(error_message) and not is_database_error:
                print(f"\nRequest limit/network issue detected for {ticker}: {error_message}")
                print(f"Sleeping {int(cooldown_seconds)} seconds, then retrying same ticker...")
                time.sleep(cooldown_seconds)
                attempt = 1
                continue

            print(f"Retry {attempt}/{max_retries} for {ticker}: {error_message}")

            if attempt < max_retries:
                time.sleep(retry_sleep_seconds)

            attempt += 1

    return result


def normalize_universe_tickers(
    tickers: list[str],
    limit: Optional[int] = None,
) -> list[str]:
    """
    Normalize and deduplicate a supplied ticker universe while preserving order.
    """

    normalized_tickers: list[str] = []
    seen: set[str] = set()

    for ticker in tickers:
        clean_ticker = str(ticker).upper().strip()

        if not clean_ticker:
            continue

        if clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        normalized_tickers.append(clean_ticker)

    if limit is not None:
        return normalized_tickers[:limit]

    return normalized_tickers


def ingest_us_universe(
    tickers: Optional[list[str]] = None,
    limit: Optional[int] = None,
    eligible_csv_path: str = "results/us_universe_eligible_tickers.csv",
    sleep_seconds: float = 0.25,
    market_period: str = "1y",
    market_interval: str = "1d",
    years_back: int = 1,
    include_quarterly: bool = True,
    output_csv_path: str = "results/us_universe_refresh_results.csv",
    force_refresh: bool = True,
    max_retries: int = 3,
    retry_sleep_seconds: float = 10.0,
    cooldown_seconds: float = 3600.0,
) -> pd.DataFrame:
    """
    Refresh market and fundamental inputs for a stock universe.

    When tickers are supplied, that exact normalized universe is refreshed.
    Otherwise, tickers are loaded from the eligible-universe CSV.
    """

    if tickers is None:
        clean_tickers = fetch_us_universe_tickers(
            limit=limit,
            eligible_csv_path=eligible_csv_path,
        )
    else:
        clean_tickers = normalize_universe_tickers(
            tickers=tickers,
            limit=limit,
        )

    if not clean_tickers:
        raise ValueError(
            "No valid tickers were supplied for universe ingestion."
        )

    tickers = clean_tickers
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
            force_refresh=force_refresh,
            max_retries=max_retries,
            retry_sleep_seconds=retry_sleep_seconds,
            cooldown_seconds=cooldown_seconds,
        )

        results.append(result)
        pd.DataFrame(results).to_csv(output_csv_path, index=False)

        if result["success"]:
            print(
                f"SUCCESS {ticker}: "
                f"market_rows={result['market_rows']}, "
                f"financial_rows={result['financial_rows']}, "
                f"skipped_existing={result['skipped_existing']}"
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

__all__ = [
    "fetch_us_universe_tickers",
    "normalize_universe_tickers",
    "get_existing_storage_status",
    "ingest_one_ticker",
    "ingest_us_universe",
]