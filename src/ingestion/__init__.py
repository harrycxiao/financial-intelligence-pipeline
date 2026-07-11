# src/ingestion/__init__.py

"""
Public interface for external data ingestion.

The package exposes the primary fetch functions used to retrieve and
normalize company metadata, market data, financial metrics, SEC filings,
and company news before persistence in the database.
"""

from src.ingestion.company_ingestion import (
    fetch_company_metadata,
    normalize_exchange,
)

from src.ingestion.financial_metrics_ingestion import (
    fetch_financial_metrics,
)

from src.ingestion.market_data_ingestion import (
    fetch_market_data,
)

from src.ingestion.news_ingestion import (
    fetch_news_articles,
)

from src.ingestion.sec_ingestion import (
    fetch_sec_filings,
    get_cik_for_ticker,
)


__all__ = [
    "fetch_company_metadata",
    "normalize_exchange",
    "fetch_market_data",
    "fetch_financial_metrics",
    "fetch_sec_filings",
    "fetch_news_articles",
    "get_cik_for_ticker",
]