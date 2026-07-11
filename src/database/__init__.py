# src/database/__init__.py

"""
Database persistence and query interface.

This package exposes the shared SQLAlchemy connection objects, the public
query package, and the primary storage functions used by ingestion workflows.
"""

from src.database.connection import (
    Base,
    SessionLocal,
    engine,
)

from src.database import query

from src.database.store import (
    store_company,
    store_financial_metrics,
    store_market_data,
    store_news_articles,
    store_sec_filings,
)


__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "query",
    "store_company",
    "store_financial_metrics",
    "store_market_data",
    "store_news_articles",
    "store_sec_filings",
]