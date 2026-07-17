# src/database/query/company_queries.py

from typing import Optional

from src.database.connection import SessionLocal
from src.database.models import Company


def company_to_dict(company: Company) -> dict:
    """Convert a Company ORM object into a plain dictionary."""

    return {
        "company_id": company.id,
        "ticker": company.ticker,
        "name": company.name,
        "sector": company.sector,
        "industry": company.industry,
        "exchange": company.exchange,
        "cik": company.cik,
        "created_at": company.created_at,
    }


def get_company_by_ticker(ticker: str) -> Optional[dict]:
    """Get one company by ticker."""

    session = SessionLocal()

    try:
        ticker = ticker.upper().strip()

        company = (
            session.query(Company)
            .filter(Company.ticker == ticker)
            .first()
        )

        if company is None:
            return None

        return company_to_dict(company)

    finally:
        session.close()


def get_company_id_by_ticker(ticker: str) -> Optional[int]:
    """Get the internal company ID for a ticker."""

    session = SessionLocal()

    try:
        ticker = ticker.upper().strip()

        company = (
            session.query(Company)
            .filter(Company.ticker == ticker)
            .first()
        )

        if company is None:
            return None

        return company.id

    finally:
        session.close()


def get_all_companies() -> list[dict]:
    """Get all companies currently stored in the database."""

    session = SessionLocal()

    try:
        companies = (
            session.query(Company)
            .order_by(Company.ticker)
            .all()
        )

        return [company_to_dict(company) for company in companies]

    finally:
        session.close()


def get_companies_by_sector(sector: str) -> list[dict]:
    """Get all companies matching a given sector."""

    session = SessionLocal()

    try:
        companies = (
            session.query(Company)
            .filter(Company.sector == sector)
            .order_by(Company.ticker)
            .all()
        )

        return [company_to_dict(company) for company in companies]

    finally:
        session.close()


def company_exists(ticker: str) -> bool:
    """Check whether a company exists in the database."""

    return get_company_id_by_ticker(ticker) is not None


def get_company_by_id(company_id: int) -> Optional[dict]:
    """Get one company by internal database ID."""

    session = SessionLocal()

    try:
        company = (
            session.query(Company)
            .filter(Company.id == company_id)
            .first()
        )

        if company is None:
            return None

        return company_to_dict(company)

    finally:
        session.close()