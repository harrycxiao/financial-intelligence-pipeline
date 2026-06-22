from fastapi import APIRouter

from src.database.store import (
    store_company,
    store_financial_metrics,
    store_market_data,
    store_news_articles,
    store_sec_filings,
)

from src.ingestion.company_ingestion import fetch_company_metadata
from src.ingestion.financial_metrics_ingestion import fetch_financial_metrics
from src.ingestion.market_data_ingestion import fetch_market_data
from src.ingestion.news_ingestion import fetch_news_articles
from src.ingestion.sec_ingestion import fetch_sec_filings


router = APIRouter(prefix="/api/refresh", tags=["Refresh / Store"])


@router.post("/company/{ticker}")
def refresh_company(ticker: str) -> dict:
    metadata = fetch_company_metadata(ticker)
    store_company(metadata)

    return {
        "message": "Company metadata refreshed.",
        "ticker": ticker.upper().strip(),
    }


@router.post("/market-data/{ticker}")
def refresh_market_data(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
) -> dict:
    metadata = fetch_company_metadata(ticker)
    store_company(metadata)

    df = fetch_market_data(ticker, period=period, interval=interval)
    store_market_data(ticker, df)

    return {
        "message": "Market data refreshed.",
        "ticker": ticker.upper().strip(),
        "rows_fetched": len(df),
    }


@router.post("/financial-metrics/{ticker}")
def refresh_financial_metrics(ticker: str, years_back: int = 5) -> dict:
    metadata = fetch_company_metadata(ticker)
    store_company(metadata)

    df = fetch_financial_metrics(ticker, years_back=years_back)
    store_financial_metrics(ticker, df)

    return {
        "message": "Financial metrics refreshed.",
        "ticker": ticker.upper().strip(),
        "rows_fetched": len(df),
    }


@router.post("/sec-filings/{ticker}")
def refresh_sec_filings(ticker: str) -> dict:
    metadata = fetch_company_metadata(ticker)
    store_company(metadata)

    df = fetch_sec_filings(ticker)
    store_sec_filings(ticker, df)

    return {
        "message": "SEC filings refreshed.",
        "ticker": ticker.upper().strip(),
        "rows_fetched": len(df),
    }


@router.post("/news/{ticker}")
def refresh_news_articles(
    ticker: str,
    days_back: int = 90,
    max_articles: int = 100,
) -> dict:
    metadata = fetch_company_metadata(ticker)
    store_company(metadata)

    df = fetch_news_articles(
        ticker=ticker,
        days_back=days_back,
        max_articles=max_articles,
    )
    store_news_articles(ticker, df)

    return {
        "message": "News articles refreshed.",
        "ticker": ticker.upper().strip(),
        "rows_fetched": len(df),
    }


@router.post("/all/{ticker}")
def refresh_all(ticker: str) -> dict:
    ticker = ticker.upper().strip()

    metadata = fetch_company_metadata(ticker)
    store_company(metadata)

    market_df = fetch_market_data(ticker)
    store_market_data(ticker, market_df)

    financial_df = fetch_financial_metrics(ticker)
    store_financial_metrics(ticker, financial_df)

    filings_df = fetch_sec_filings(ticker)
    store_sec_filings(ticker, filings_df)

    news_df = fetch_news_articles(ticker)
    store_news_articles(ticker, news_df)

    return {
        "message": "Full pipeline refreshed.",
        "ticker": ticker,
        "market_data_rows": len(market_df),
        "financial_metric_rows": len(financial_df),
        "sec_filing_rows": len(filings_df),
        "news_article_rows": len(news_df),
    }