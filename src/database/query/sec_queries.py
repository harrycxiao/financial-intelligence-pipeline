# src/database/query/sec_queries.py

from typing import Optional

from src.database.connection import SessionLocal
from src.database.models import Filing
from src.database.query.company_queries import get_company_id_by_ticker


def filing_to_dict(filing: Filing, include_raw_text: bool = False) -> dict:
    """Convert a Filing ORM object into a plain dictionary."""

    data = {
        "filing_id": filing.id,
        "company_id": filing.company_id,
        "filing_type": filing.filing_type,
        "filing_date": filing.filing_date,
        "accession_number": filing.accession_number,
        "filing_url": filing.filing_url,
        "summary": filing.summary,
        "created_at": filing.created_at,
    }

    if include_raw_text:
        data["raw_text"] = filing.raw_text

    return data


def get_sec_filings(ticker: str, include_raw_text: bool = False) -> list[dict]:
    """Get all stored SEC filings for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        filings = (
            session.query(Filing)
            .filter(Filing.company_id == company_id)
            .order_by(Filing.filing_date.desc())
            .all()
        )

        return [
            filing_to_dict(filing, include_raw_text=include_raw_text)
            for filing in filings
        ]

    finally:
        session.close()


def get_latest_sec_filing(
    ticker: str,
    filing_type: Optional[str] = None,
    include_raw_text: bool = False,
) -> Optional[dict]:
    """Get the latest SEC filing, optionally filtered by filing type."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return None

        query = session.query(Filing).filter(Filing.company_id == company_id)

        if filing_type is not None:
            query = query.filter(Filing.filing_type == filing_type.upper().strip())

        filing = query.order_by(Filing.filing_date.desc()).first()

        if filing is None:
            return None

        return filing_to_dict(filing, include_raw_text=include_raw_text)

    finally:
        session.close()


def get_sec_filings_by_type(
    ticker: str,
    filing_type: str,
    include_raw_text: bool = False,
) -> list[dict]:
    """Get stored SEC filings for a ticker and filing type."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        filing_type = filing_type.upper().strip()

        filings = (
            session.query(Filing)
            .filter(
                Filing.company_id == company_id,
                Filing.filing_type == filing_type,
            )
            .order_by(Filing.filing_date.desc())
            .all()
        )

        return [
            filing_to_dict(filing, include_raw_text=include_raw_text)
            for filing in filings
        ]

    finally:
        session.close()


def get_recent_sec_filings(
    ticker: str,
    limit: int = 5,
    include_raw_text: bool = False,
) -> list[dict]:
    """Get the most recent stored SEC filings for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        filings = (
            session.query(Filing)
            .filter(Filing.company_id == company_id)
            .order_by(Filing.filing_date.desc())
            .limit(limit)
            .all()
        )

        return [
            filing_to_dict(filing, include_raw_text=include_raw_text)
            for filing in filings
        ]

    finally:
        session.close()


def get_filing_by_accession_number(
    accession_number: str,
    include_raw_text: bool = True,
) -> Optional[dict]:
    """Get one filing by SEC accession number."""

    session = SessionLocal()

    try:
        filing = (
            session.query(Filing)
            .filter(Filing.accession_number == accession_number)
            .first()
        )

        if filing is None:
            return None

        return filing_to_dict(filing, include_raw_text=include_raw_text)

    finally:
        session.close()