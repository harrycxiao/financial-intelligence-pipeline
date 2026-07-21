# src/ai/services/__init__.py

"""
Public orchestration-service interface for the AI research layer.

Services coordinate deterministic tools and construct complete validated
research contexts. They do not call an LLM or generate final report objects.
"""

from src.ai.services.research_service import (
    build_holding_research_context,
    build_portfolio_context_from_result,
    extract_company_quantitative_context,
    prepare_company_research_context,
    prepare_quarterly_research_context,
)

from src.ai.services.store_universe_tickers import (
    fetch_us_universe_tickers,
    normalize_universe_tickers,
    get_existing_storage_status,
    ingest_one_ticker,
    ingest_us_universe,
)

__all__ = [
    "prepare_quarterly_research_context",
    "build_portfolio_context_from_result",
    "prepare_company_research_context",
    "build_holding_research_context",
    "extract_company_quantitative_context",
    "fetch_us_universe_tickers",
    "normalize_universe_tickers",
    "get_existing_storage_status",
    "ingest_one_ticker",
    "ingest_us_universe",
]