# src/database/store.py

from sqlalchemy.exc import SQLAlchemyError

from src.database.connection import SessionLocal
from src.database.models import Company, MarketPrice


# ---------------------------------------------------------------------
# Company storage
# ---------------------------------------------------------------------


def store_company(metadata: dict) -> Company:
    """Insert or update a company metadata row."""

    session = SessionLocal()

    try:
        ticker = metadata["ticker"].upper().strip()

        company = (
            session.query(Company)
            .filter(Company.ticker == ticker)
            .first()
        )

        if company is None:
            company = Company(
                ticker=ticker,
                name=metadata["name"],
                sector=metadata.get("sector"),
                industry=metadata.get("industry"),
                exchange=metadata.get("exchange"),
                cik=metadata.get("cik"),
            )

            session.add(company)

        else:
            company.name = metadata.get("name", company.name)
            company.sector = metadata.get("sector", company.sector)
            company.industry = metadata.get("industry", company.industry)
            company.exchange = metadata.get("exchange", company.exchange)
            company.cik = metadata.get("cik", company.cik)

        session.commit()
        session.refresh(company)

        return company

    except SQLAlchemyError as e:
        session.rollback()
        raise e

    finally:
        session.close()


# ---------------------------------------------------------------------
# Market data storage
# ---------------------------------------------------------------------


def store_market_data(ticker: str, df) -> None:
    """Store historical market price rows for an existing company."""

    session = SessionLocal()

    try:
        ticker = ticker.upper().strip()

        company = (
            session.query(Company)
            .filter(Company.ticker == ticker)
            .first()
        )

        if company is None:
            raise ValueError(
                f"Company '{ticker}' not found. Store company metadata first."
            )

        company_id = company.id

        for _, row in df.iterrows():
            row_date = row["date"].date()

            existing_price = (
                session.query(MarketPrice)
                .filter(
                    MarketPrice.company_id == company_id,
                    MarketPrice.date == row_date,
                )
                .first()
            )

            if existing_price is not None:
                continue

            market_price = MarketPrice(
                company_id=company_id,
                date=row_date,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                adjusted_close=float(row["adjusted_close"]),
                volume=int(row["volume"]),
            )

            session.add(market_price)

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise e

    finally:
        session.close()