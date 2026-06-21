# src/database/query/news_queries.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from src.database.connection import SessionLocal
from src.database.models import NewsArticle
from src.database.query.company_queries import get_company_id_by_ticker


def news_article_to_dict(article: NewsArticle, include_raw_text: bool = False) -> dict:
    """Convert a NewsArticle ORM object into a plain dictionary."""

    data = {
        "news_article_id": article.id,
        "company_id": article.company_id,
        "title": article.title,
        "source": article.source,
        "author": article.author,
        "published_at": article.published_at,
        "url": article.url,
        "summary": article.summary,
        "sentiment_score": article.sentiment_score,
        "created_at": article.created_at,
    }

    if include_raw_text:
        data["raw_text"] = article.raw_text

    return data


def get_news_articles(ticker: str, include_raw_text: bool = False) -> list[dict]:
    """Get all stored news articles for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        articles = (
            session.query(NewsArticle)
            .filter(NewsArticle.company_id == company_id)
            .order_by(NewsArticle.published_at.desc())
            .all()
        )

        return [
            news_article_to_dict(article, include_raw_text=include_raw_text)
            for article in articles
        ]

    finally:
        session.close()


def get_recent_news_articles(
    ticker: str,
    days: int = 30,
    include_raw_text: bool = False,
) -> list[dict]:
    """Get news articles published in the last N days."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        articles = (
            session.query(NewsArticle)
            .filter(
                NewsArticle.company_id == company_id,
                NewsArticle.published_at >= cutoff,
            )
            .order_by(NewsArticle.published_at.desc())
            .all()
        )

        return [
            news_article_to_dict(article, include_raw_text=include_raw_text)
            for article in articles
        ]

    finally:
        session.close()


def get_latest_news_article(
    ticker: str,
    include_raw_text: bool = False,
) -> Optional[dict]:
    """Get the most recent stored news article for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return None

        article = (
            session.query(NewsArticle)
            .filter(NewsArticle.company_id == company_id)
            .order_by(NewsArticle.published_at.desc())
            .first()
        )

        if article is None:
            return None

        return news_article_to_dict(article, include_raw_text=include_raw_text)

    finally:
        session.close()


def get_news_articles_by_source(
    ticker: str,
    source: str,
    include_raw_text: bool = False,
) -> list[dict]:
    """Get news articles for a ticker from a specific source."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        articles = (
            session.query(NewsArticle)
            .filter(
                NewsArticle.company_id == company_id,
                NewsArticle.source == source,
            )
            .order_by(NewsArticle.published_at.desc())
            .all()
        )

        return [
            news_article_to_dict(article, include_raw_text=include_raw_text)
            for article in articles
        ]

    finally:
        session.close()


def search_news_articles(
    ticker: str,
    keyword: str,
    include_raw_text: bool = False,
) -> list[dict]:
    """Search stored news articles by keyword in title or summary."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        keyword_pattern = f"%{keyword}%"

        articles = (
            session.query(NewsArticle)
            .filter(
                NewsArticle.company_id == company_id,
                (
                    NewsArticle.title.ilike(keyword_pattern)
                    | NewsArticle.summary.ilike(keyword_pattern)
                ),
            )
            .order_by(NewsArticle.published_at.desc())
            .all()
        )

        return [
            news_article_to_dict(article, include_raw_text=include_raw_text)
            for article in articles
        ]

    finally:
        session.close()


def get_news_article_by_url(
    url: str,
    include_raw_text: bool = True,
) -> Optional[dict]:
    """Get one news article by URL."""

    session = SessionLocal()

    try:
        article = (
            session.query(NewsArticle)
            .filter(NewsArticle.url == url)
            .first()
        )

        if article is None:
            return None

        return news_article_to_dict(article, include_raw_text=include_raw_text)

    finally:
        session.close()


def get_news_articles_count(ticker: str) -> int:
    """Count stored news articles for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return 0

        return (
            session.query(NewsArticle)
            .filter(NewsArticle.company_id == company_id)
            .count()
        )

    finally:
        session.close()