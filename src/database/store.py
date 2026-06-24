# src/database/store.py

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from src.database.connection import SessionLocal
from src.database.models import Company, Filing, FinancialMetric, MarketPrice, NewsArticle


def clean_float(value):
    """Convert NaN values from pandas into None before storing in Postgres."""

    if pd.isna(value):
        return None

    return float(value)


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
                open=clean_float(row["open"]),
                high=clean_float(row["high"]),
                low=clean_float(row["low"]),
                close=clean_float(row["close"]),
                adjusted_close=clean_float(row["adjusted_close"]),
                volume=int(row["volume"]) if not pd.isna(row["volume"]) else None,
                shares_outstanding=int(row["shares_outstanding"])
                if "shares_outstanding" in row and not pd.isna(row["shares_outstanding"])
                else None,
            )

            session.add(market_price)

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise e

    finally:
        session.close()


# ---------------------------------------------------------------------
# Financial metrics storage
# ---------------------------------------------------------------------


def store_financial_metrics(ticker: str, df) -> None:
    """Store annual financial metrics for an existing company."""

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

        # SEC ingestion gives us reliable CIK data, so update the company row.
        if not df.empty and "cik" in df.columns and not pd.isna(df.iloc[0]["cik"]):
            company.cik = str(df.iloc[0]["cik"])

        for _, row in df.iterrows():
            period_end_date = pd.to_datetime(row["period_end_date"]).date()
            fiscal_period = row.get("fiscal_period")

            existing_metric = (
                session.query(FinancialMetric)
                .filter(
                    FinancialMetric.company_id == company_id,
                    FinancialMetric.period_end_date == period_end_date,
                    FinancialMetric.fiscal_period == fiscal_period,
                )
                .first()
            )

            if existing_metric is not None:
                continue

            if existing_metric is None:
                existing_metric = FinancialMetric(
                    company_id=company_id,
                    period_end_date=period_end_date,
                    fiscal_period=fiscal_period,
                )
                session.add(existing_metric)

            existing_metric.fiscal_year = int(row["fiscal_year"]) if not pd.isna(row["fiscal_year"]) else None
            existing_metric.revenue = clean_float(row.get("revenue"))
            existing_metric.net_income = clean_float(row.get("net_income"))
            existing_metric.operating_income = clean_float(row.get("operating_income"))
            existing_metric.gross_profit = clean_float(row.get("gross_profit"))

            existing_metric.total_assets = clean_float(row.get("total_assets"))
            existing_metric.total_liabilities = clean_float(row.get("total_liabilities"))
            existing_metric.cash_and_equivalents = clean_float(row.get("cash_and_equivalents"))
            existing_metric.total_debt = clean_float(row.get("total_debt"))

            existing_metric.operating_cash_flow = clean_float(row.get("operating_cash_flow"))
            existing_metric.free_cash_flow = clean_float(row.get("free_cash_flow"))

            existing_metric.capital_expenditures = clean_float(row.get("capital_expenditures"))
            existing_metric.depreciation_and_amortization = clean_float(row.get("depreciation_and_amortization"))
            existing_metric.r_and_d_expense = clean_float(row.get("r_and_d_expense"))
            existing_metric.sga_expense = clean_float(row.get("sga_expense"))

            existing_metric.current_assets = clean_float(row.get("current_assets"))
            existing_metric.current_liabilities = clean_float(row.get("current_liabilities"))
            existing_metric.inventory = clean_float(row.get("inventory"))
            existing_metric.accounts_receivable = clean_float(row.get("accounts_receivable"))
            existing_metric.accounts_payable = clean_float(row.get("accounts_payable"))

            existing_metric.interest_expense = clean_float(row.get("interest_expense"))
            existing_metric.income_tax_expense = clean_float(row.get("income_tax_expense"))
            existing_metric.dividends_paid = clean_float(row.get("dividends_paid"))

            existing_metric.weighted_average_shares = clean_float(row.get("weighted_average_shares"))
            existing_metric.weighted_average_diluted_shares = clean_float(row.get("weighted_average_diluted_shares"))

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise e

    finally:
        session.close()


# ---------------------------------------------------------------------
# SEC filings storage
# ---------------------------------------------------------------------


def store_sec_filings(ticker: str, df) -> None:
    """Store SEC filing metadata and raw text for an existing company."""

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

        # SEC filing ingestion also gives reliable CIK data.
        if not df.empty and "cik" in df.columns and not pd.isna(df.iloc[0]["cik"]):
            company.cik = str(df.iloc[0]["cik"])

        for _, row in df.iterrows():
            accession_number = row.get("accession_number")

            existing_filing = (
                session.query(Filing)
                .filter(Filing.accession_number == accession_number)
                .first()
            )

            if existing_filing is None:
                existing_filing = Filing(
                    company_id=company_id,
                    accession_number=accession_number,
                )
                session.add(existing_filing)

            existing_filing.filing_type = row.get("filing_type")
            existing_filing.filing_date = pd.to_datetime(row["filing_date"]).date()
            existing_filing.filing_url = row.get("filing_url")
            existing_filing.raw_text = row.get("raw_text")
            existing_filing.summary = row.get("summary")

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise e

    finally:
        session.close()


# ---------------------------------------------------------------------
# News articles storage
# ---------------------------------------------------------------------


def store_news_articles(ticker: str, df) -> None:
    """Store recent company news articles for an existing company."""

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
            url = row.get("url")

            existing_article = (
                session.query(NewsArticle)
                .filter(NewsArticle.url == url)
                .first()
            )

            if existing_article is not None:
                continue

            article = NewsArticle(
                company_id=company_id,
                title=row.get("title"),
                source=row.get("source"),
                author=row.get("author"),
                published_at=row.get("published_at"),
                url=url,
                raw_text=row.get("raw_text"),
                summary=row.get("summary"),
                sentiment_score=clean_float(row.get("sentiment_score")),
            )

            session.add(article)

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise e

    finally:
        session.close()