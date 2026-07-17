# src/ai/tools/company_tools.py

"""
Deterministic company-data tools for the AI layer.

These functions retrieve, refresh, clean, and organize company metadata,
fundamental history, market metrics, and technical indicators.

This module does not:
- run quantitative factor or alpha models;
- retrieve news or SEC filing text;
- call an LLM;
- construct final Pydantic research-context or report objects.

Higher-level orchestration belongs in research_service.py.
"""

from datetime import date, datetime
import math
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from src.analytics.derived_metrics.fundamental_analysis import (
    calculate_fundamental_summary,
    get_fundamental_dataframe,
)

from src.analytics.derived_metrics.market_analysis import (
    calculate_market_summary,
)

from src.analytics.derived_metrics.technical_indicators import (
    calculate_latest_technical_snapshot,
)

from src.database import (
    query,
    store_company,
    store_financial_metrics,
    store_market_data,
)

from src.ingestion import (
    fetch_company_metadata,
    fetch_financial_metrics,
    fetch_market_data,
)


# ---------------------------------------------------------------------
# Internal column definitions
# ---------------------------------------------------------------------


COMPANY_METADATA_OUTPUT_COLUMNS = [
    "ticker",
    "company_name",
    "sector",
    "industry",
    "exchange",
    "cik",
]


FINANCIAL_INTERNAL_COLUMNS = {
    "financial_metric_id",
    "company_id",
    "created_at",
}


VALID_PERIOD_MODES = {
    "quarterly",
    "annual",
    "raw",
}


# ---------------------------------------------------------------------
# General normalization helpers
# ---------------------------------------------------------------------


def normalize_ticker(ticker: str) -> str:
    """Normalize and validate one ticker symbol."""

    clean_ticker = str(ticker).upper().strip()

    if not clean_ticker:
        raise ValueError("ticker cannot be empty.")

    return clean_ticker


def normalize_ticker_list(tickers: Iterable[str]) -> List[str]:
    """Normalize and deduplicate tickers while preserving order."""

    normalized = []
    seen = set()

    for ticker in tickers:
        clean_ticker = normalize_ticker(ticker)

        if clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        normalized.append(clean_ticker)

    return normalized


def to_python_value(value: Any) -> Any:
    """
    Convert Pandas and NumPy values into ordinary Python values.

    Date and datetime objects are preserved because the AI service remains
    inside Python. JSON conversion belongs at an API or persistence boundary.
    """

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, np.ndarray):
        return [
            to_python_value(item)
            for item in value.tolist()
        ]

    if isinstance(value, np.generic):
        return to_python_value(value.item())

    if isinstance(value, dict):
        return {
            str(key): to_python_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            to_python_value(item)
            for item in value
        ]

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

        return value

    try:
        missing = pd.isna(value)

        if isinstance(missing, (bool, np.bool_)) and bool(missing):
            return None
    except (TypeError, ValueError):
        pass

    return value


def dataframe_to_records(
    df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """Convert a DataFrame into clean Python record dictionaries."""

    if df is None or df.empty:
        return []

    records = df.to_dict(orient="records")

    return [
        {
            str(key): to_python_value(value)
            for key, value in record.items()
        }
        for record in records
    ]


def clean_record(
    record: Dict[str, Any],
    excluded_columns: Optional[set] = None,
) -> Dict[str, Any]:
    """Clean one dictionary and optionally remove internal columns."""

    excluded = excluded_columns or set()

    return {
        str(key): to_python_value(value)
        for key, value in record.items()
        if key not in excluded
    }


# ---------------------------------------------------------------------
# Company metadata
# ---------------------------------------------------------------------


def clean_company_metadata(
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert database or ingestion metadata into the AI-layer format.

    The database and ingestion layers use `name`; the AI layer consistently
    uses the less ambiguous field name `company_name`.
    """

    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dictionary.")

    ticker_value = metadata.get("ticker")

    if ticker_value is None:
        raise ValueError(
            "Company metadata must contain a ticker."
        )

    ticker = normalize_ticker(ticker_value)

    company_name = (
        metadata.get("company_name")
        or metadata.get("name")
        or ticker
    )

    return {
        "ticker": ticker,
        "company_name": to_python_value(company_name),
        "sector": to_python_value(metadata.get("sector")),
        "industry": to_python_value(metadata.get("industry")),
        "exchange": to_python_value(metadata.get("exchange")),
        "cik": to_python_value(metadata.get("cik")),
    }


def refresh_company_metadata(
    ticker: str,
) -> Dict[str, Any]:
    """
    Fetch and upsert current company metadata, then return the stored record.
    """

    clean_ticker = normalize_ticker(ticker)

    fetched_metadata = fetch_company_metadata(clean_ticker)
    store_company(fetched_metadata)

    stored_metadata = query.get_company_by_ticker(clean_ticker)

    if stored_metadata is None:
        raise RuntimeError(
            f"Company metadata for {clean_ticker} was fetched but "
            "could not be retrieved after storage."
        )

    return clean_company_metadata(stored_metadata)


def get_company_metadata(
    ticker: str,
    refresh_if_missing: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve normalized company metadata from the database.

    When refresh_if_missing is True, metadata is fetched and stored only
    when the company is not already present in the database.
    """

    clean_ticker = normalize_ticker(ticker)
    stored_metadata = query.get_company_by_ticker(clean_ticker)

    if stored_metadata is not None:
        return clean_company_metadata(stored_metadata)

    if not refresh_if_missing:
        return None

    return refresh_company_metadata(clean_ticker)


def ensure_company_metadata(
    ticker: str,
) -> Dict[str, Any]:
    """
    Return stored metadata, fetching and storing it when necessary.

    Refresh functions use this before storing related market or fundamental
    rows because those rows require an existing company database record.
    """

    metadata = get_company_metadata(
        ticker=ticker,
        refresh_if_missing=True,
    )

    if metadata is None:
        raise RuntimeError(
            f"Unable to retrieve or create metadata for {ticker}."
        )

    return metadata


# ---------------------------------------------------------------------
# Fundamental history and summaries
# ---------------------------------------------------------------------


def clean_financial_record(
    record: Dict[str, Any],
) -> Dict[str, Any]:
    """Remove database-only fields from one financial-history record."""

    return clean_record(
        record=record,
        excluded_columns=FINANCIAL_INTERNAL_COLUMNS,
    )


def get_company_financial_history(
    ticker: str,
    as_of_date: date,
    limit: int = 12,
    period_mode: str = "quarterly",
) -> List[Dict[str, Any]]:
    """
    Return point-in-time fundamental history for one company.

    For quarterly mode, get_fundamental_dataframe reconstructs Q4 using the
    annual FY row minus Q1, Q2, and Q3 flow values.

    Results are returned newest first and limited to the requested number
    of periods.
    """

    clean_ticker = normalize_ticker(ticker)

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    if period_mode not in VALID_PERIOD_MODES:
        raise ValueError(
            "period_mode must be one of: quarterly, annual, raw."
        )

    financial_df = get_fundamental_dataframe(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        period_mode=period_mode,
    )

    if financial_df.empty:
        return []

    result = financial_df.copy()

    if "period_end_date" in result.columns:
        result["period_end_date"] = pd.to_datetime(
            result["period_end_date"],
            errors="coerce",
        )

        result = result.sort_values(
            "period_end_date",
            ascending=False,
        )

    result = result.head(limit).reset_index(drop=True)

    records = dataframe_to_records(result)

    return [
        clean_financial_record(record)
        for record in records
    ]


def get_company_fundamental_summary(
    ticker: str,
    as_of_date: date,
    period_mode: str = "quarterly",
) -> Dict[str, Any]:
    """
    Return latest derived fundamental metrics and annual CAGR information.
    """

    clean_ticker = normalize_ticker(ticker)

    if period_mode not in VALID_PERIOD_MODES:
        raise ValueError(
            "period_mode must be one of: quarterly, annual, raw."
        )

    summary = calculate_fundamental_summary(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        period_mode=period_mode,
    )

    return to_python_value(summary)


def refresh_company_financial_metrics(
    ticker: str,
    years_back: int = 1,
    include_quarterly: bool = True,
) -> Dict[str, Any]:
    """
    Fetch and store recent SEC company-fact financial metrics.

    years_back=1 is normally enough for recurring quarterly refreshes because
    the historical database rows already remain stored. A larger value may be
    supplied for new companies or historical backfills.
    """

    clean_ticker = normalize_ticker(ticker)

    if years_back < 1:
        raise ValueError("years_back must be at least 1.")

    ensure_company_metadata(clean_ticker)

    count_before = query.get_financial_metrics_count(clean_ticker)

    financial_df = fetch_financial_metrics(
        ticker=clean_ticker,
        years_back=years_back,
        include_quarterly=include_quarterly,
    )

    store_financial_metrics(
        clean_ticker,
        financial_df,
    )

    count_after = query.get_financial_metrics_count(clean_ticker)

    return {
        "ticker": clean_ticker,
        "rows_fetched": int(len(financial_df)),
        "stored_count_before": int(count_before),
        "stored_count_after": int(count_after),
        "new_rows_added": int(max(count_after - count_before, 0)),
        "years_back": years_back,
        "include_quarterly": include_quarterly,
    }


# ---------------------------------------------------------------------
# Market data, market metrics, and technical indicators
# ---------------------------------------------------------------------


def refresh_company_market_data(
    ticker: str,
    recent_period: str = "6mo",
    bootstrap_period: str = "5y",
    interval: str = "1d",
) -> Dict[str, Any]:
    """
    Fetch and store market data.

    Companies already present in the database receive a lightweight recent
    refresh. Companies with no stored market history receive a larger initial
    historical backfill.
    """

    clean_ticker = normalize_ticker(ticker)
    ensure_company_metadata(clean_ticker)

    count_before = query.get_market_data_count(clean_ticker)

    requested_period = (
        bootstrap_period
        if count_before == 0
        else recent_period
    )

    market_df = fetch_market_data(
        ticker=clean_ticker,
        period=requested_period,
        interval=interval,
    )

    store_market_data(
        clean_ticker,
        market_df,
    )

    count_after = query.get_market_data_count(clean_ticker)

    first_date = None
    last_date = None

    if not market_df.empty and "date" in market_df.columns:
        raw_dates = market_df.loc[:, "date"]

        fetched_dates = pd.Series(
            pd.to_datetime(
                raw_dates,
                errors="coerce",
            ),
            index=market_df.index,
        ).dropna()

        if not fetched_dates.empty:
            first_date = to_python_value(fetched_dates.min())
            last_date = to_python_value(fetched_dates.max())

    return {
        "ticker": clean_ticker,
        "rows_fetched": int(len(market_df)),
        "stored_count_before": int(count_before),
        "stored_count_after": int(count_after),
        "new_rows_added": int(max(count_after - count_before, 0)),
        "requested_period": requested_period,
        "refresh_type": (
            "initial_backfill"
            if count_before == 0
            else "recent_refresh"
        ),
        "interval": interval,
        "first_fetched_date": first_date,
        "last_fetched_date": last_date,
    }


def get_company_market_summary(
    ticker: str,
    as_of_date: date,
) -> Dict[str, Any]:
    """
    Return compact market metrics and the latest technical snapshot.

    The requested as-of date and the actual latest market-observation date
    are both preserved because they are not necessarily identical.
    """

    clean_ticker = normalize_ticker(ticker)

    market_metrics = to_python_value(
        calculate_market_summary(
            ticker=clean_ticker,
            as_of_date=as_of_date,
        )
    )

    technical_snapshot = to_python_value(
        calculate_latest_technical_snapshot(
            ticker=clean_ticker,
            as_of_date=as_of_date,
        )
    )

    if isinstance(market_metrics, dict):
        market_metrics.pop("ticker", None)
        market_metrics.pop("as_of_date", None)

    technical_indicators = None

    if isinstance(technical_snapshot, dict):
        if "technical_indicators" in technical_snapshot:
            # This is the explicit empty-result representation.
            technical_indicators = technical_snapshot.get(
                "technical_indicators"
            )
        else:
            technical_snapshot.pop("ticker", None)
            technical_indicators = technical_snapshot

    return {
        "ticker": clean_ticker,
        "as_of_date": as_of_date,
        "market_metrics": market_metrics,
        "technical_indicators": technical_indicators,
    }


# ---------------------------------------------------------------------
# Combined refresh workflow
# ---------------------------------------------------------------------


def refresh_company_core_data(
    ticker: str,
    market_recent_period: str = "6mo",
    market_bootstrap_period: str = "5y",
    market_interval: str = "1d",
    financial_years_back: int = 1,
    include_quarterly: bool = True,
) -> Dict[str, Any]:
    """
    Refresh metadata, recent market prices, and recent financial statements.
    """

    clean_ticker = normalize_ticker(ticker)

    metadata = refresh_company_metadata(clean_ticker)

    market_refresh = refresh_company_market_data(
        ticker=clean_ticker,
        recent_period=market_recent_period,
        bootstrap_period=market_bootstrap_period,
        interval=market_interval,
    )

    financial_refresh = refresh_company_financial_metrics(
        ticker=clean_ticker,
        years_back=financial_years_back,
        include_quarterly=include_quarterly,
    )

    return {
        "ticker": clean_ticker,
        "company_metadata": metadata,
        "market_refresh": market_refresh,
        "financial_refresh": financial_refresh,
    }


# ---------------------------------------------------------------------
# Company-domain research bundles
# ---------------------------------------------------------------------


def build_company_data_warnings(
    ticker: str,
    as_of_date: date,
    metadata: Optional[Dict[str, Any]],
    financial_history: List[Dict[str, Any]],
    market_summary: Dict[str, Any],
) -> List[str]:
    """Build deterministic data-quality warnings for one company."""

    clean_ticker = normalize_ticker(ticker)
    warnings = []

    if metadata is None:
        warnings.append(
            f"No stored company metadata was available for "
            f"{clean_ticker}."
        )

    if not financial_history:
        warnings.append(
            f"No point-in-time fundamental history was available for "
            f"{clean_ticker} as of {as_of_date.isoformat()}."
        )
    elif len(financial_history) < 4:
        warnings.append(
            f"Fewer than four quarterly fundamental records were "
            f"available for {clean_ticker}."
        )

    market_metrics = market_summary.get(
        "market_metrics",
        {},
    )

    if not market_metrics:
        warnings.append(
            f"No market summary was available for {clean_ticker}."
        )

    technical_indicators = market_summary.get(
        "technical_indicators"
    )

    if not technical_indicators:
        warnings.append(
            f"No technical-indicator snapshot was available for "
            f"{clean_ticker}."
        )
    elif isinstance(technical_indicators, dict):
        technical_date = technical_indicators.get("date")

        if technical_date is not None:
            if isinstance(technical_date, datetime):
                technical_date = technical_date.date()

            if isinstance(technical_date, date):
                age_days = (
                    as_of_date - technical_date
                ).days

                if age_days > 10:
                    warnings.append(
                        f"The latest market observation for "
                        f"{clean_ticker} was {age_days} calendar days "
                        f"before the requested as-of date."
                    )

    return warnings


def get_company_core_research_data(
    ticker: str,
    as_of_date: date,
    financial_history_limit: int = 12,
    period_mode: str = "quarterly",
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = False,
) -> Dict[str, Any]:
    """
    Build the company-domain data bundle used by research services.

    refresh_if_missing fills completely absent company datasets.

    refresh_recent_data performs a current external refresh even when the
    company already has stored data. This should normally remain False for
    historical point-in-time research.

    This includes:
    - company identity and classification;
    - point-in-time fundamental history;
    - latest derived fundamental summary;
    - market behavior metrics;
    - latest technical indicators;
    - deterministic data-quality warnings.

    Quantitative factor/alpha results, news, and filings are intentionally
    handled by other tool modules.
    """
    clean_ticker = normalize_ticker(ticker)

    if refresh_recent_data:
        refresh_company_core_data(
            ticker=clean_ticker,
            market_recent_period="6mo",
            market_bootstrap_period="5y",
            financial_years_back=1,
            include_quarterly=True,
        )

    metadata = get_company_metadata(
        ticker=clean_ticker,
        refresh_if_missing=refresh_if_missing,
    )

    if refresh_if_missing and not refresh_recent_data:
        if query.get_market_data_count(clean_ticker) == 0:
            refresh_company_market_data(
                ticker=clean_ticker,
            )

        if query.get_financial_metrics_count(clean_ticker) == 0:
            refresh_company_financial_metrics(
                ticker=clean_ticker,
            )

    financial_history = get_company_financial_history(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        limit=financial_history_limit,
        period_mode=period_mode,
    )

    fundamental_summary = get_company_fundamental_summary(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        period_mode=period_mode,
    )

    market_summary = get_company_market_summary(
        ticker=clean_ticker,
        as_of_date=as_of_date,
    )

    warnings = build_company_data_warnings(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        metadata=metadata,
        financial_history=financial_history,
        market_summary=market_summary,
    )

    return {
        "ticker": clean_ticker,
        "company_metadata": metadata,
        "financial_history": financial_history,
        "fundamental_summary": fundamental_summary,
        "market_history_summary": market_summary,
        "data_warnings": warnings,
    }


def get_company_core_research_data_for_tickers(
    tickers: Iterable[str],
    as_of_date: date,
    financial_history_limit: int = 12,
    period_mode: str = "quarterly",
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    Build company-domain research bundles for multiple tickers.

    Errors are isolated by ticker so one unavailable company does not prevent
    the remaining companies from receiving research context.
    """

    clean_tickers = normalize_ticker_list(tickers)
    results = {}

    for ticker in clean_tickers:
        try:
            results[ticker] = get_company_core_research_data(
                ticker=ticker,
                as_of_date=as_of_date,
                financial_history_limit=financial_history_limit,
                period_mode=period_mode,
                refresh_if_missing=refresh_if_missing,
                refresh_recent_data=refresh_recent_data,
            )

        except Exception as error:
            results[ticker] = {
                "ticker": ticker,
                "company_metadata": None,
                "financial_history": [],
                "fundamental_summary": {},
                "market_history_summary": {},
                "data_warnings": [
                    (
                        "Unable to build company research data for "
                        f"{ticker}: {error}"
                    )
                ],
            }

    return results


__all__ = [
    "clean_company_metadata",
    "clean_financial_record",
    "get_company_metadata",
    "refresh_company_metadata",
    "ensure_company_metadata",
    "get_company_financial_history",
    "get_company_fundamental_summary",
    "refresh_company_financial_metrics",
    "refresh_company_market_data",
    "get_company_market_summary",
    "refresh_company_core_data",
    "build_company_data_warnings",
    "get_company_core_research_data",
    "get_company_core_research_data_for_tickers",
]