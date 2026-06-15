from sqlalchemy.exc import SQLAlchemyError

from src.database.connection import SessionLocal
from src.database.models import Company


def store_company(metadata: dict) -> Company:

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
