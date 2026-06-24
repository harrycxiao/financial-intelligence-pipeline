# src/database/query/financial_metrics_queries.py

from typing import Optional

from src.database.connection import SessionLocal
from src.database.models import FinancialMetric
from src.database.query.company_queries import get_company_id_by_ticker


def financial_metric_to_dict(metric: FinancialMetric) -> dict:
    """Convert a FinancialMetric ORM object into a plain dictionary."""

    return {
        "financial_metric_id": metric.id,
        "company_id": metric.company_id,
        "period_end_date": metric.period_end_date,
        "fiscal_year": metric.fiscal_year,
        "fiscal_period": metric.fiscal_period,
        "revenue": metric.revenue,
        "net_income": metric.net_income,
        "operating_income": metric.operating_income,
        "gross_profit": metric.gross_profit,
        "total_assets": metric.total_assets,
        "total_liabilities": metric.total_liabilities,
        "cash_and_equivalents": metric.cash_and_equivalents,
        "total_debt": metric.total_debt,
        "operating_cash_flow": metric.operating_cash_flow,
        "free_cash_flow": metric.free_cash_flow,
        "created_at": metric.created_at,
        "capital_expenditures": metric.capital_expenditures,
        "depreciation_and_amortization": metric.depreciation_and_amortization,
        "r_and_d_expense": metric.r_and_d_expense,
        "sga_expense": metric.sga_expense,
        "current_assets": metric.current_assets,
        "current_liabilities": metric.current_liabilities,
        "inventory": metric.inventory,
        "accounts_receivable": metric.accounts_receivable,
        "accounts_payable": metric.accounts_payable,
        "interest_expense": metric.interest_expense,
        "income_tax_expense": metric.income_tax_expense,
        "dividends_paid": metric.dividends_paid,
        "weighted_average_shares": metric.weighted_average_shares,
        "weighted_average_diluted_shares": metric.weighted_average_diluted_shares,
    }


def get_financial_metrics(ticker: str) -> list[dict]:
    """Get all stored financial metrics for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        metrics = (
            session.query(FinancialMetric)
            .filter(FinancialMetric.company_id == company_id)
            .order_by(FinancialMetric.period_end_date.desc())
            .all()
        )

        return [financial_metric_to_dict(metric) for metric in metrics]

    finally:
        session.close()


def get_latest_financial_metrics(ticker: str) -> Optional[dict]:
    """Get the most recent financial metrics row for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return None

        metric = (
            session.query(FinancialMetric)
            .filter(FinancialMetric.company_id == company_id)
            .order_by(FinancialMetric.period_end_date.desc())
            .first()
        )

        if metric is None:
            return None

        return financial_metric_to_dict(metric)

    finally:
        session.close()


def get_financial_metrics_between_years(
    ticker: str,
    start_year: int,
    end_year: int,
) -> list[dict]:
    """Get financial metrics between fiscal years, inclusive."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return []

        metrics = (
            session.query(FinancialMetric)
            .filter(
                FinancialMetric.company_id == company_id,
                FinancialMetric.fiscal_year >= start_year,
                FinancialMetric.fiscal_year <= end_year,
            )
            .order_by(FinancialMetric.fiscal_year.desc())
            .all()
        )

        return [financial_metric_to_dict(metric) for metric in metrics]

    finally:
        session.close()


def get_financial_metrics_count(ticker: str) -> int:
    """Count stored financial metric rows for a ticker."""

    session = SessionLocal()

    try:
        company_id = get_company_id_by_ticker(ticker)

        if company_id is None:
            return 0

        return (
            session.query(FinancialMetric)
            .filter(FinancialMetric.company_id == company_id)
            .count()
        )

    finally:
        session.close()