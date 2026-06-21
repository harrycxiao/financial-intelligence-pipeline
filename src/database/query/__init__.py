# src/database/query/__init__.py

"""
Read-only query layer for the financial intelligence pipeline.
"""

from src.database.query.company_queries import (
    company_exists,
    get_all_companies,
    get_companies_by_sector,
    get_company_by_ticker,
    get_company_id_by_ticker,
)

from src.database.query.market_data_queries import (
    get_latest_market_price,
    get_market_data,
    get_market_data_between_dates,
    get_market_data_count,
    get_recent_market_data,
)

from src.database.query.financial_metrics_queries import (
    get_financial_metrics,
    get_financial_metrics_between_years,
    get_financial_metrics_count,
    get_latest_financial_metrics,
)

from src.database.query.sec_queries import (
    get_filing_by_accession_number,
    get_latest_sec_filing,
    get_recent_sec_filings,
    get_sec_filings,
    get_sec_filings_by_type,
)

from src.database.query.news_queries import (
    get_latest_news_article,
    get_news_article_by_url,
    get_news_articles,
    get_news_articles_by_source,
    get_news_articles_count,
    get_recent_news_articles,
    search_news_articles,
)