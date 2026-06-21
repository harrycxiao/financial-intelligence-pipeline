# src/database/query/market_data_queries.py

from datetime import date, timedelta
from typing import Optional

from src.database.connection import SessionLocal
from src.database.models import MarketPrice
from src.database.query.company_queries import get_company_id_by_ticker


def market_price_to_dict(price: MarketPrice) -> dict:
    """Convert a MarketPrice ORM object into a plain dictionary."""

    return {
        "market_price_id": price.id,
        "company_id": price.company_id,
        "date": price.date,
        "open": price.open,
        "high": price.high,
        "low": price.low,
        "close": price.close,
        "adjusted_close": price.adjusted_close,
        "volume": price.volume,
        "created_at": price.created_at,
    }


def get_market_data(ticker: str) -> list[dict]:
    """Get all stored market data for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        prices = (
            session.query(MarketPrice)
            .filter(MarketPrice.company_id == company_id)
            .order_by(MarketPrice.date.desc())
            .all()
        )

        return [market_price_to_dict(price) for price in prices]

    finally:
        session.close()


def get_latest_market_price(ticker: str) -> Optional[dict]:
    """Get the most recent stored market price row for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return None

        price = (
            session.query(MarketPrice)
            .filter(MarketPrice.company_id == company_id)
            .order_by(MarketPrice.date.desc())
            .first()
        )

        if price is None:
            return None

        return market_price_to_dict(price)

    finally:
        session.close()


def get_market_data_between_dates(
    ticker: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Get market data between two dates, inclusive."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        prices = (
            session.query(MarketPrice)
            .filter(
                MarketPrice.company_id == company_id,
                MarketPrice.date >= start_date,
                MarketPrice.date <= end_date,
            )
            .order_by(MarketPrice.date.desc())
            .all()
        )

        return [market_price_to_dict(price) for price in prices]

    finally:
        session.close()


def get_recent_market_data(ticker: str, days: int = 30) -> list[dict]:
    """Get market data from the last N calendar days."""

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    return get_market_data_between_dates(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )


def get_market_data_count(ticker: str) -> int:
    """Count stored market price rows for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return 0

        return (
            session.query(MarketPrice)
            .filter(MarketPrice.company_id == company_id)
            .count()
        )

    finally:
        session.close()