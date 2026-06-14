from datetime import date as PythonDate, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.connection import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    sector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cik: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    market_prices: Mapped[list["MarketPrice"]] = relationship(back_populates="company")
    filings: Mapped[list["Filing"]] = relationship(back_populates="company")
    news_articles: Mapped[list["NewsArticle"]] = relationship(back_populates="company")
    financial_metrics: Mapped[list["FinancialMetric"]] = relationship(back_populates="company")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    date: Mapped[PythonDate] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjusted_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company: Mapped["Company"] = relationship(back_populates="market_prices")

    __table_args__ = (
        UniqueConstraint("company_id", "date", name="uq_market_price_company_date"),
    )


class Filing(Base):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    filing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filing_date: Mapped[PythonDate] = mapped_column(Date, nullable=False, index=True)
    accession_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    filing_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company: Mapped["Company"] = relationship(back_populates="filings")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)

    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company: Mapped["Company"] = relationship(back_populates="news_articles")


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    period_end_date: Mapped[PythonDate] = mapped_column(Date, nullable=False, index=True)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fiscal_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    total_assets: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_debt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    operating_cash_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    free_cash_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company: Mapped["Company"] = relationship(back_populates="financial_metrics")

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "period_end_date",
            "fiscal_period",
            name="uq_financial_metric_company_period",
        ),
    )