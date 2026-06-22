from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.database import query


router = APIRouter(prefix="/api", tags=["Query"])


# ---------------------------------------------------------------------
# Company query endpoints
# ---------------------------------------------------------------------


@router.get("/companies")
def get_all_companies() -> list[dict]:
    return query.get_all_companies()


@router.get("/companies/{ticker}")
def get_company(ticker: str) -> dict:
    company = query.get_company_by_ticker(ticker)

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")

    return company


@router.get("/companies/{ticker}/exists")
def company_exists(ticker: str) -> dict:
    return {
        "ticker": ticker.upper().strip(),
        "exists": query.company_exists(ticker),
    }


@router.get("/companies/sector/{sector}")
def get_companies_by_sector(sector: str) -> list[dict]:
    return query.get_companies_by_sector(sector)


# ---------------------------------------------------------------------
# Market data query endpoints
# ---------------------------------------------------------------------


@router.get("/market-data/{ticker}")
def get_market_data(ticker: str) -> list[dict]:
    return query.get_market_data(ticker)


@router.get("/market-data/{ticker}/latest")
def get_latest_market_price(ticker: str) -> dict:
    price = query.get_latest_market_price(ticker)

    if price is None:
        raise HTTPException(status_code=404, detail="Market price not found.")

    return price


@router.get("/market-data/{ticker}/between")
def get_market_data_between_dates(
    ticker: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    return query.get_market_data_between_dates(ticker, start_date, end_date)


@router.get("/market-data/{ticker}/recent")
def get_recent_market_data(ticker: str, days: int = 30) -> list[dict]:
    return query.get_recent_market_data(ticker, days=days)


@router.get("/market-data/{ticker}/count")
def get_market_data_count(ticker: str) -> dict:
    return {
        "ticker": ticker.upper().strip(),
        "count": query.get_market_data_count(ticker),
    }


# ---------------------------------------------------------------------
# Financial metrics query endpoints
# ---------------------------------------------------------------------


@router.get("/financial-metrics/{ticker}")
def get_financial_metrics(ticker: str) -> list[dict]:
    return query.get_financial_metrics(ticker)


@router.get("/financial-metrics/{ticker}/latest")
def get_latest_financial_metrics(ticker: str) -> dict:
    metrics = query.get_latest_financial_metrics(ticker)

    if metrics is None:
        raise HTTPException(status_code=404, detail="Financial metrics not found.")

    return metrics


@router.get("/financial-metrics/{ticker}/between-years")
def get_financial_metrics_between_years(
    ticker: str,
    start_year: int,
    end_year: int,
) -> list[dict]:
    return query.get_financial_metrics_between_years(ticker, start_year, end_year)


@router.get("/financial-metrics/{ticker}/count")
def get_financial_metrics_count(ticker: str) -> dict:
    return {
        "ticker": ticker.upper().strip(),
        "count": query.get_financial_metrics_count(ticker),
    }


# ---------------------------------------------------------------------
# SEC filing query endpoints
# ---------------------------------------------------------------------


@router.get("/sec-filings/{ticker}")
def get_sec_filings(
    ticker: str,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.get_sec_filings(ticker, include_raw_text=include_raw_text)


@router.get("/sec-filings/{ticker}/latest")
def get_latest_sec_filing(
    ticker: str,
    filing_type: Optional[str] = None,
    include_raw_text: bool = False,
) -> dict:
    filing = query.get_latest_sec_filing(
        ticker=ticker,
        filing_type=filing_type,
        include_raw_text=include_raw_text,
    )

    if filing is None:
        raise HTTPException(status_code=404, detail="SEC filing not found.")

    return filing


@router.get("/sec-filings/{ticker}/type/{filing_type}")
def get_sec_filings_by_type(
    ticker: str,
    filing_type: str,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.get_sec_filings_by_type(
        ticker=ticker,
        filing_type=filing_type,
        include_raw_text=include_raw_text,
    )


@router.get("/sec-filings/{ticker}/recent")
def get_recent_sec_filings(
    ticker: str,
    limit: int = 5,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.get_recent_sec_filings(
        ticker=ticker,
        limit=limit,
        include_raw_text=include_raw_text,
    )


@router.get("/sec-filings/accession/{accession_number}")
def get_filing_by_accession_number(
    accession_number: str,
    include_raw_text: bool = True,
) -> dict:
    filing = query.get_filing_by_accession_number(
        accession_number=accession_number,
        include_raw_text=include_raw_text,
    )

    if filing is None:
        raise HTTPException(status_code=404, detail="SEC filing not found.")

    return filing


# ---------------------------------------------------------------------
# News query endpoints
# ---------------------------------------------------------------------


@router.get("/news/{ticker}")
def get_news_articles(
    ticker: str,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.get_news_articles(ticker, include_raw_text=include_raw_text)


@router.get("/news/{ticker}/recent")
def get_recent_news_articles(
    ticker: str,
    days: int = 30,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.get_recent_news_articles(
        ticker=ticker,
        days=days,
        include_raw_text=include_raw_text,
    )


@router.get("/news/{ticker}/latest")
def get_latest_news_article(
    ticker: str,
    include_raw_text: bool = False,
) -> dict:
    article = query.get_latest_news_article(
        ticker=ticker,
        include_raw_text=include_raw_text,
    )

    if article is None:
        raise HTTPException(status_code=404, detail="News article not found.")

    return article


@router.get("/news/{ticker}/source/{source}")
def get_news_articles_by_source(
    ticker: str,
    source: str,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.get_news_articles_by_source(
        ticker=ticker,
        source=source,
        include_raw_text=include_raw_text,
    )


@router.get("/news/{ticker}/search")
def search_news_articles(
    ticker: str,
    keyword: str,
    include_raw_text: bool = False,
) -> list[dict]:
    return query.search_news_articles(
        ticker=ticker,
        keyword=keyword,
        include_raw_text=include_raw_text,
    )


@router.get("/news/by-url")
def get_news_article_by_url(
    url: str,
    include_raw_text: bool = True,
) -> dict:
    article = query.get_news_article_by_url(
        url=url,
        include_raw_text=include_raw_text,
    )

    if article is None:
        raise HTTPException(status_code=404, detail="News article not found.")

    return article


@router.get("/news/{ticker}/count")
def get_news_articles_count(ticker: str) -> dict:
    return {
        "ticker": ticker.upper().strip(),
        "count": query.get_news_articles_count(ticker),
    }