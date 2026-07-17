# src/ai/tools/__init__.py

"""
Public deterministic-tool interface for the AI research layer.

These tools retrieve, refresh, clean, rank, and structure evidence. They do
not call an LLM or generate final investment reports.

Higher-level orchestration belongs in src.ai.services.
"""

# ---------------------------------------------------------------------
# Quantitative research tools
# ---------------------------------------------------------------------

from src.ai.tools.quant_tools import (
    extract_portfolio_weights,
    get_research_engine_configuration,
    get_ticker_research_record,
    run_quantitative_research,
    split_quantitative_record,
    split_selected_quantitative_records,
    summarize_quantitative_research,
)


# ---------------------------------------------------------------------
# Company-data tools
# ---------------------------------------------------------------------

from src.ai.tools.company_tools import (
    ensure_company_metadata,
    get_company_core_research_data,
    get_company_metadata,
)


# ---------------------------------------------------------------------
# SEC-filing tools
# ---------------------------------------------------------------------

from src.ai.tools.filing_tools import (
    DEFAULT_HOLDING_FORM_LIMITS,
    DEFAULT_RESEARCH_FORM_LIMITS,
    DEFAULT_REFRESH_FORM_LIMITS,
    build_filing_evidence,
    get_company_filings,
    get_filing_by_accession,
    get_filing_evidence,
    get_filing_evidence_for_tickers,
    get_holding_filing_evidence,
    get_holding_filing_evidence_for_tickers,
    get_latest_company_filing,
    refresh_company_filings,
)


# ---------------------------------------------------------------------
# Company-news tools
# ---------------------------------------------------------------------

from src.ai.tools.news_tools import (
    DEFAULT_HOLDING_NEWS_DAYS_BACK,
    DEFAULT_HOLDING_NEWS_LIMIT,
    DEFAULT_RESEARCH_NEWS_DAYS_BACK,
    DEFAULT_RESEARCH_NEWS_LIMIT,
    DEFAULT_REFRESH_MAX_ARTICLES,
    DEFAULT_REFRESH_NEWS_DAYS_BACK,
    build_news_evidence,
    get_company_news,
    get_holding_news_evidence,
    get_holding_news_evidence_for_tickers,
    get_latest_company_news,
    get_news_article_by_url,
    get_news_evidence,
    get_news_evidence_for_tickers,
    refresh_company_news,
)


__all__ = [
    # Quantitative research
    "run_quantitative_research",
    "summarize_quantitative_research",
    "get_research_engine_configuration",
    "extract_portfolio_weights",
    "get_ticker_research_record",
    "split_quantitative_record",
    "split_selected_quantitative_records",

    # Company data
    "ensure_company_metadata",
    "get_company_metadata",
    "get_company_core_research_data",

    # Filing configuration
    "DEFAULT_RESEARCH_FORM_LIMITS",
    "DEFAULT_HOLDING_FORM_LIMITS",
    "DEFAULT_REFRESH_FORM_LIMITS",

    # Filing operations
    "refresh_company_filings",
    "get_company_filings",
    "get_latest_company_filing",
    "get_filing_by_accession",
    "build_filing_evidence",
    "get_filing_evidence",
    "get_holding_filing_evidence",
    "get_filing_evidence_for_tickers",
    "get_holding_filing_evidence_for_tickers",

    # News configuration
    "DEFAULT_RESEARCH_NEWS_DAYS_BACK",
    "DEFAULT_RESEARCH_NEWS_LIMIT",
    "DEFAULT_HOLDING_NEWS_DAYS_BACK",
    "DEFAULT_HOLDING_NEWS_LIMIT",
    "DEFAULT_REFRESH_NEWS_DAYS_BACK",
    "DEFAULT_REFRESH_MAX_ARTICLES",

    # News operations
    "refresh_company_news",
    "get_company_news",
    "get_latest_company_news",
    "get_news_article_by_url",
    "build_news_evidence",
    "get_news_evidence",
    "get_holding_news_evidence",
    "get_news_evidence_for_tickers",
    "get_holding_news_evidence_for_tickers",
]