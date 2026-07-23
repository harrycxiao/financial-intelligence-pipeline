# src/ai/services/research_service.py

"""
Deterministic research-context orchestration for the AI layer.

This service coordinates the lower-level quantitative, company, news, and
SEC-filing tools and constructs validated research-context schemas.

Main workflows:
- QuarterlyResearchRequest -> PortfolioResearchContext
- CompanyResearchRequest -> CompanyResearchContext

This module does not:
- call an LLM;
- generate QuarterlyPortfolioReport or CompanyResearchReport;
- change portfolio selections or quantitative weights;
- calculate factor scores or expected returns itself;
- expose raw full-universe DataFrames to the LLM.

The agent layer receives the completed context objects and interprets them.
"""

import math
from typing import Any, Dict, Iterable, List, Optional

from src.ai.schemas.research_schemas import (
    CompanyResearchContext,
    CompanyResearchRequest,
    FilingEvidence,
    HoldingResearchContext,
    NewsEvidence,
    PortfolioResearchContext,
    QuarterlyResearchRequest,
)

from src.ai.tools.company_tools import (
    get_company_core_research_data,
    get_company_metadata,
)

from src.ai.tools.filing_tools import (
    get_filing_evidence,
    get_holding_filing_evidence_for_tickers,
)

from src.ai.tools.news_tools import (
    get_news_evidence,
    get_news_evidence_for_tickers,
)

from src.ai.tools.quant_tools import (
    extract_portfolio_weights,
    get_research_engine_configuration,
    get_ticker_research_record,
    run_quantitative_research,
    split_quantitative_record,
    split_selected_quantitative_records,
    summarize_quantitative_research,
)

from src.ai.services.store_universe_tickers import (
    ingest_us_universe,
)

# ---------------------------------------------------------------------
# Service configuration
# ---------------------------------------------------------------------


# Portfolio holdings already contain factor-engine derived metrics, so the
# quarterly portfolio context only needs basic company metadata plus compact
# news and filing evidence.
DEFAULT_PORTFOLIO_REFRESH_IF_MISSING = True


# A standalone company report uses quarterly financial history by default.
DEFAULT_COMPANY_PERIOD_MODE = "quarterly"


# News currently consists mainly of Finnhub title-and-summary evidence.
NEWS_SUMMARY_LIMITATION = (
    "News evidence is primarily based on Finnhub titles and short summaries. "
    "A full publisher article was not reviewed unless raw_text_excerpt is "
    "present for that evidence item."
)


MODEL_LIMITATION = (
    "Expected excess returns are statistical model estimates and should not "
    "be interpreted as guaranteed future returns."
)


# ---------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------


def normalize_ticker(ticker: str) -> str:
    """Normalize and validate one ticker symbol."""

    clean_ticker = str(ticker).upper().strip()

    if not clean_ticker:
        raise ValueError("ticker cannot be empty.")

    return clean_ticker


def normalize_ticker_list(
    tickers: Iterable[str],
) -> List[str]:
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


def safe_optional_float(
    value: Any,
) -> Optional[float]:
    """Convert a finite numeric value into float or return None."""

    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(numeric_value):
        return None

    return numeric_value


def safe_nonnegative_int(
    value: Any,
    default: int = 0,
) -> int:
    """Convert a value into a nonnegative integer."""

    if value is None:
        return default

    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return default

    return max(numeric_value, 0)


def clean_optional_text(
    value: Any,
) -> Optional[str]:
    """Return stripped text or None."""

    if value is None:
        return None

    clean_value = str(value).strip()

    if not clean_value:
        return None

    return clean_value


def deduplicate_messages(
    messages: Iterable[str],
) -> List[str]:
    """Remove duplicate warning or freshness messages while preserving order."""

    result = []
    seen = set()

    for message in messages:
        clean_message = clean_optional_text(message)

        if clean_message is None:
            continue

        if clean_message in seen:
            continue

        seen.add(clean_message)
        result.append(clean_message)

    return result


def has_full_news_text(
    evidence: Iterable[NewsEvidence],
) -> bool:
    """Return True when at least one news item contains a raw-text excerpt."""

    return any(
        clean_optional_text(item.raw_text_excerpt) is not None
        for item in evidence
    )


# ---------------------------------------------------------------------
# Holding warning construction
# ---------------------------------------------------------------------


def build_holding_data_warnings(
    ticker: str,
    company_metadata: Optional[Dict[str, Any]],
    quantitative_data: Dict[str, Any],
    news_evidence: List[NewsEvidence],
    filing_evidence: List[FilingEvidence],
    include_news: bool,
    include_filings: bool,
    portfolio_weight_available: bool,
) -> List[str]:
    """Build deterministic evidence warnings for one selected holding."""

    clean_ticker = normalize_ticker(ticker)
    warnings = []

    if not company_metadata:
        warnings.append(
            f"Company metadata was unavailable for {clean_ticker}."
        )
    else:
        if not clean_optional_text(
            company_metadata.get("company_name")
        ):
            warnings.append(
                f"Company name was unavailable for {clean_ticker}."
            )

        if not clean_optional_text(
            company_metadata.get("sector")
        ):
            warnings.append(
                f"Sector classification was unavailable for {clean_ticker}."
            )

        if not clean_optional_text(
            company_metadata.get("industry")
        ):
            warnings.append(
                f"Industry classification was unavailable for {clean_ticker}."
            )

    if not quantitative_data:
        warnings.append(
            f"Quantitative research data was unavailable for {clean_ticker}."
        )
    else:
        if quantitative_data.get("universe_rank") is None:
            warnings.append(
                f"Universe rank was unavailable for {clean_ticker}."
            )

        if quantitative_data.get("screen_rank") is None:
            warnings.append(
                f"Screen rank was unavailable for {clean_ticker}."
            )

        if quantitative_data.get("overall_score") is None:
            warnings.append(
                f"Overall factor score was unavailable for {clean_ticker}."
            )

        if quantitative_data.get("expected_excess_return") is None:
            warnings.append(
                "The statistical expected-excess-return estimate was "
                f"unavailable for {clean_ticker}."
            )

        factor_scores = quantitative_data.get(
            "factor_scores",
            {},
        )

        if not factor_scores:
            warnings.append(
                f"Factor-category scores were unavailable for {clean_ticker}."
            )

        derived_metrics = quantitative_data.get(
            "derived_metrics",
            {},
        )

        if not derived_metrics:
            warnings.append(
                f"Underlying derived metrics were unavailable for "
                f"{clean_ticker}."
            )

    if not portfolio_weight_available:
        warnings.append(
            f"No portfolio weight was returned for {clean_ticker}; "
            "the context uses a zero weight as a defensive fallback."
        )

    if include_news:
        if not news_evidence:
            warnings.append(
                "No qualifying recent news evidence was found for "
                f"{clean_ticker}."
            )
        elif not has_full_news_text(news_evidence):
            warnings.append(
                NEWS_SUMMARY_LIMITATION
            )

    if include_filings and not filing_evidence:
        warnings.append(
            "No qualifying supported SEC filing evidence was found for "
            f"{clean_ticker}."
        )

    return deduplicate_messages(warnings)


# ---------------------------------------------------------------------
# One-holding context construction
# ---------------------------------------------------------------------


def build_holding_research_context(
    ticker: str,
    quantitative_data: Dict[str, Any],
    portfolio_weight: float,
    company_metadata: Optional[Dict[str, Any]] = None,
    news_evidence: Optional[List[NewsEvidence]] = None,
    filing_evidence: Optional[List[FilingEvidence]] = None,
    include_news: bool = True,
    include_filings: bool = True,
    portfolio_weight_available: bool = True,
) -> HoldingResearchContext:
    """
    Construct one validated HoldingResearchContext.

    The quantitative engine remains authoritative for ranks, scores, expected
    return, selection, and portfolio weight. This function only maps those
    outputs together with supporting company, news, and filing evidence.
    """

    clean_ticker = normalize_ticker(ticker)

    metadata = company_metadata or {}
    recent_news = list(news_evidence or [])
    recent_filings = list(filing_evidence or [])

    quantitative_ticker = quantitative_data.get(
        "ticker"
    )

    if quantitative_ticker is not None:
        normalized_quant_ticker = normalize_ticker(
            quantitative_ticker
        )

        if normalized_quant_ticker != clean_ticker:
            raise ValueError(
                "Quantitative ticker does not match the requested holding: "
                f"{normalized_quant_ticker} != {clean_ticker}."
            )

    numeric_weight = safe_optional_float(
        portfolio_weight
    )

    if numeric_weight is None:
        numeric_weight = 0.0

    if numeric_weight < 0.0 or numeric_weight > 1.0:
        raise ValueError(
            f"Portfolio weight for {clean_ticker} must be between 0 and 1."
        )

    warnings = build_holding_data_warnings(
        ticker=clean_ticker,
        company_metadata=metadata,
        quantitative_data=quantitative_data,
        news_evidence=recent_news,
        filing_evidence=recent_filings,
        include_news=include_news,
        include_filings=include_filings,
        portfolio_weight_available=portfolio_weight_available,
    )

    return HoldingResearchContext(
        ticker=clean_ticker,
        company_name=clean_optional_text(
            metadata.get("company_name")
        ),
        sector=clean_optional_text(
            metadata.get("sector")
        ),
        industry=clean_optional_text(
            metadata.get("industry")
        ),
        portfolio_weight=numeric_weight,
        universe_rank=quantitative_data.get(
            "universe_rank"
        ),
        screen_rank=quantitative_data.get(
            "screen_rank"
        ),
        overall_score=safe_optional_float(
            quantitative_data.get("overall_score")
        ),
        expected_excess_return=safe_optional_float(
            quantitative_data.get(
                "expected_excess_return"
            )
        ),
        factor_scores=dict(
            quantitative_data.get(
                "factor_scores",
                {},
            )
            or {}
        ),
        derived_metrics=dict(
            quantitative_data.get(
                "derived_metrics",
                {},
            )
            or {}
        ),
        recent_news=recent_news,
        recent_filings=recent_filings,
        data_warnings=warnings,
    )


# ---------------------------------------------------------------------
# Portfolio-level notes and warnings
# ---------------------------------------------------------------------


def build_portfolio_freshness_notes(
    request: QuarterlyResearchRequest,
) -> List[str]:
    """Describe deterministic data-timing behavior for a portfolio context."""

    notes = [
        (
            "Quantitative, filing, and news evidence was evaluated using "
            f"the requested as-of date of {request.as_of_date.isoformat()}."
        ),
        (
            "Records dated after the requested as-of date are excluded by "
            "the point-in-time retrieval tools."
        ),
    ]

    if request.use_cache:
        notes.append(
            "The quantitative engine was allowed to reuse cached factor and "
            "predictive-model snapshots when available."
        )
    else:
        notes.append(
            "The quantitative engine was instructed not to reuse cached "
            "factor or predictive-model snapshots."
        )

    if request.refresh_recent_data:
        notes.append(
            "A current external-data refresh was requested before supporting "
            "company, news, or filing evidence was assembled."
        )
    else:
        notes.append(
            "Existing stored supporting data was used unless a required "
            "company dataset was completely missing."
        )

    if request.include_news:
        notes.append(
            NEWS_SUMMARY_LIMITATION
        )

    return deduplicate_messages(notes)


def build_portfolio_warnings(
    request: QuarterlyResearchRequest,
    selected_tickers: List[str],
    holdings: List[HoldingResearchContext],
    portfolio_weights: Dict[str, float],
) -> List[str]:
    """Build overall deterministic warnings for a portfolio context."""

    warnings = [
        MODEL_LIMITATION,
    ]

    if not selected_tickers:
        warnings.append(
            "The quantitative engine did not return selected tickers."
        )

    missing_holding_contexts = (
        set(selected_tickers)
        - {holding.ticker for holding in holdings}
    )

    if missing_holding_contexts:
        warnings.append(
            "Holding contexts were unavailable for: "
            f"{sorted(missing_holding_contexts)}."
        )

    missing_weights = (
        set(selected_tickers)
        - set(portfolio_weights.keys())
    )

    if missing_weights:
        warnings.append(
            "Portfolio weights were unavailable for: "
            f"{sorted(missing_weights)}."
        )

    weight_sum = sum(
        portfolio_weights.values()
    )

    if portfolio_weights and weight_sum < 0.999:
        warnings.append(
            "Portfolio weights sum to less than one; part of the portfolio "
            "may be unallocated or may have been omitted after validation."
        )

    holdings_without_news = [
        holding.ticker
        for holding in holdings
        if request.include_news and not holding.recent_news
    ]

    if holdings_without_news:
        warnings.append(
            "No qualifying news evidence was found for holdings: "
            f"{holdings_without_news}."
        )

    holdings_without_filings = [
        holding.ticker
        for holding in holdings
        if request.include_filings and not holding.recent_filings
    ]

    if holdings_without_filings:
        warnings.append(
            "No qualifying SEC filing evidence was found for holdings: "
            f"{holdings_without_filings}."
        )

    holdings_without_alpha = [
        holding.ticker
        for holding in holdings
        if holding.expected_excess_return is None
    ]

    if holdings_without_alpha:
        warnings.append(
            "Expected-excess-return estimates were unavailable for holdings: "
            f"{holdings_without_alpha}."
        )

    return deduplicate_messages(warnings)


# ---------------------------------------------------------------------
# Portfolio-context construction from an existing research result
# ---------------------------------------------------------------------


def build_portfolio_context_from_result(
    request: QuarterlyResearchRequest,
    research_result: Dict[str, Any],
) -> PortfolioResearchContext:
    """
    Construct PortfolioResearchContext from an existing quantitative result.

    This function is useful when:
    - the expensive research-engine result has already been calculated;
    - a saved result is being reloaded;
    - prompts or agents are being tested repeatedly;
    - only supporting evidence or context construction needs to be rerun.
    """

    if not isinstance(request, QuarterlyResearchRequest):
        raise TypeError(
            "request must be a QuarterlyResearchRequest."
        )

    if not isinstance(research_result, dict):
        raise TypeError(
            "research_result must be a dictionary."
        )

    quantitative_summary = summarize_quantitative_research(
        research_result
    )

    selected_tickers = normalize_ticker_list(
        quantitative_summary.get(
            "selected_tickers",
            [],
        )
    )

    if not selected_tickers:
        raise ValueError(
            "Cannot build portfolio context without selected tickers."
        )

    screened_tickers = normalize_ticker_list(
        quantitative_summary.get(
            "screened_tickers",
            [],
        )
    )

    portfolio_weights = extract_portfolio_weights(
        research_result
    )

    split_quantitative_records = (
        split_selected_quantitative_records(
            research_result
        )
    )

    # -------------------------------------------------------------
    # Retrieve company identity metadata for the selected holdings.
    # Full financial histories are intentionally not added to each
    # holding because factor-engine derived metrics already provide
    # compact quantitative evidence.
    # -------------------------------------------------------------

    metadata_by_ticker: Dict[
        str,
        Optional[Dict[str, Any]],
    ] = {}

    for ticker in selected_tickers:
        try:
            metadata_by_ticker[ticker] = get_company_metadata(
                ticker=ticker,
                refresh_if_missing=(
                    DEFAULT_PORTFOLIO_REFRESH_IF_MISSING
                ),
            )
        except Exception:
            metadata_by_ticker[ticker] = None

    # -------------------------------------------------------------
    # Retrieve compact news evidence.
    # -------------------------------------------------------------

    news_by_ticker: Dict[
        str,
        List[NewsEvidence],
    ] = {
        ticker: []
        for ticker in selected_tickers
    }

    if (
        request.include_news
        and request.max_news_articles_per_ticker > 0
    ):
        news_by_ticker = get_news_evidence_for_tickers(
            tickers=selected_tickers,
            as_of_date=request.as_of_date,
            days_back=request.news_days_back,
            limit_per_ticker=(
                request.max_news_articles_per_ticker
            ),
            refresh_if_missing=True,
            refresh_recent_data=(
                request.refresh_recent_data
            ),
            include_raw_text_excerpt=True,
        )

    # -------------------------------------------------------------
    # Retrieve compact filing evidence.
    #
    # The filing tool uses a useful holding-specific form mix.
    # filing_limit_per_ticker is applied as a final total cap.
    # -------------------------------------------------------------

    filings_by_ticker: Dict[
        str,
        List[FilingEvidence],
    ] = {
        ticker: []
        for ticker in selected_tickers
    }

    if (
        request.include_filings
        and request.filing_limit_per_ticker > 0
    ):
        raw_filings_by_ticker = (
            get_holding_filing_evidence_for_tickers(
                tickers=selected_tickers,
                as_of_date=request.as_of_date,
                refresh_if_missing=True,
                refresh_recent_data=(
                    request.refresh_recent_data
                ),
                include_excerpts=True,
            )
        )

        filings_by_ticker = {
            ticker: list(
                raw_filings_by_ticker.get(
                    ticker,
                    [],
                )
            )[:request.filing_limit_per_ticker]
            for ticker in selected_tickers
        }

    # -------------------------------------------------------------
    # Construct one validated holding context per selected ticker.
    # -------------------------------------------------------------

    holdings = []

    for ticker in selected_tickers:
        quantitative_data = (
            split_quantitative_records.get(
                ticker,
                {},
            )
        )

        if not quantitative_data:
            raw_record = get_ticker_research_record(
                research_result=research_result,
                ticker=ticker,
                full_universe=False,
            )

            if raw_record is not None:
                quantitative_data = split_quantitative_record(
                    raw_record
                )

        weight_available = ticker in portfolio_weights

        weight = portfolio_weights.get(
            ticker,
            0.0,
        )

        holding = build_holding_research_context(
            ticker=ticker,
            quantitative_data=quantitative_data,
            portfolio_weight=weight,
            company_metadata=metadata_by_ticker.get(
                ticker
            ),
            news_evidence=news_by_ticker.get(
                ticker,
                [],
            ),
            filing_evidence=filings_by_ticker.get(
                ticker,
                [],
            ),
            include_news=request.include_news,
            include_filings=request.include_filings,
            portfolio_weight_available=weight_available,
        )

        holdings.append(holding)

    configuration = get_research_engine_configuration(
        request
    )

    benchmark_ticker = clean_optional_text(
        configuration.get("benchmark_ticker")
    )

    universe_size = safe_nonnegative_int(
        quantitative_summary.get(
            "universe_size"
        ),
        default=len(request.universe_tickers),
    )

    eligible_universe_size = safe_nonnegative_int(
        quantitative_summary.get(
            "eligible_universe_size"
        ),
        default=0,
    )

    freshness_notes = build_portfolio_freshness_notes(
        request
    )

    warnings = build_portfolio_warnings(
        request=request,
        selected_tickers=selected_tickers,
        holdings=holdings,
        portfolio_weights=portfolio_weights,
    )

    return PortfolioResearchContext(
        as_of_date=request.as_of_date,
        portfolio_method=request.portfolio_method,
        period_mode=request.period_mode,
        benchmark_ticker=benchmark_ticker,
        universe_size=universe_size,
        eligible_universe_size=eligible_universe_size,
        screened_tickers=screened_tickers,
        selected_tickers=selected_tickers,
        portfolio_weights=portfolio_weights,
        holdings=holdings,
        configuration=configuration,
        data_freshness_notes=freshness_notes,
        warnings=warnings,
    )


# ---------------------------------------------------------------------
# Main quarterly service
# ---------------------------------------------------------------------


def prepare_quarterly_research_context(
    request: QuarterlyResearchRequest,
) -> PortfolioResearchContext:
    """
    Refresh optional universe-wide quantitative inputs, run the quantitative
    research engine, and assemble the final portfolio research context.

    Universe-wide market and fundamental refreshes occur before factor scoring
    and expected-return estimation.

    News and SEC-filing refreshes remain limited to selected holdings and occur
    later inside build_portfolio_context_from_result.
    """

    if not isinstance(request, QuarterlyResearchRequest):
        raise TypeError(
            "request must be a QuarterlyResearchRequest."
        )

    if request.refresh_quantitative_inputs:
        ingestion_results = ingest_us_universe(
            tickers=request.universe_tickers,
            limit=None,
            sleep_seconds=0.25,
            market_period="1y",
            market_interval="1d",
            years_back=1,
            include_quarterly=True,
            output_csv_path=(
                "results/us_universe_refresh_results.csv"
            ),
            force_refresh=True,
            max_retries=3,
            retry_sleep_seconds=10.0,
            cooldown_seconds=3600.0,
        )

        if ingestion_results.empty:
            raise RuntimeError(
                "Universe refresh returned no ingestion results."
            )

        successful_count = int(
            ingestion_results["success"].sum()
        )

        if successful_count == 0:
            raise RuntimeError(
                "Universe refresh failed for every requested ticker."
            )

        failed_count = (
            len(ingestion_results) - successful_count
        )

        print(
            "\n--- Quarterly Universe Refresh Summary ---"
        )
        print(
            f"Requested: {len(ingestion_results)}"
        )
        print(
            f"Successful: {successful_count}"
        )
        print(
            f"Failed: {failed_count}"
        )

        from src.ingestion.market_data_ingestion import fetch_market_data
        from src.database.store import store_market_data

        print(
            "\nRefreshing SPY benchmark market data..."
        )

        spy_market_data = fetch_market_data(
            ticker="SPY",
            period="1y",
            interval="1d",
        )

        store_market_data(
            ticker="SPY",
            df=spy_market_data,
        )

        print(
            "SPY benchmark market data refreshed."
        )

    research_result = run_quantitative_research(
        request
    )

    return build_portfolio_context_from_result(
        request=request,
        research_result=research_result,
    )


# ---------------------------------------------------------------------
# Company quantitative-context extraction
# ---------------------------------------------------------------------


def extract_company_quantitative_context(
    ticker: str,
    research_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Extract optional factor, rank, alpha, and portfolio information.

    A standalone company report can be produced without a quantitative result.
    When a result is supplied, full_universe=True allows lookup of any eligible
    ticker represented in that research-engine run.
    """

    clean_ticker = normalize_ticker(ticker)

    empty_context = {
        "is_current_holding": False,
        "portfolio_weight": None,
        "universe_rank": None,
        "screen_rank": None,
        "overall_score": None,
        "expected_excess_return": None,
        "factor_scores": {},
        "derived_metrics": {},
    }

    if research_result is None:
        return empty_context

    if not isinstance(research_result, dict):
        raise TypeError(
            "research_result must be a dictionary or None."
        )

    selected_tickers = normalize_ticker_list(
        research_result.get(
            "selected_tickers",
            [],
        )
    )

    portfolio_weights = extract_portfolio_weights(
        research_result
    )

    raw_record = get_ticker_research_record(
        research_result=research_result,
        ticker=clean_ticker,
        full_universe=True,
    )

    if raw_record is None:
        return {
            **empty_context,
            "is_current_holding": (
                clean_ticker in selected_tickers
            ),
            "portfolio_weight": (
                portfolio_weights.get(clean_ticker)
                if clean_ticker in selected_tickers
                else None
            ),
        }

    split_record = split_quantitative_record(
        raw_record
    )

    is_current_holding = (
        clean_ticker in selected_tickers
    )

    portfolio_weight = None

    if is_current_holding:
        portfolio_weight = portfolio_weights.get(
            clean_ticker
        )

    return {
        "is_current_holding": is_current_holding,
        "portfolio_weight": portfolio_weight,
        "universe_rank": split_record.get(
            "universe_rank"
        ),
        "screen_rank": split_record.get(
            "screen_rank"
        ),
        "overall_score": safe_optional_float(
            split_record.get("overall_score")
        ),
        "expected_excess_return": safe_optional_float(
            split_record.get(
                "expected_excess_return"
            )
        ),
        "factor_scores": dict(
            split_record.get(
                "factor_scores",
                {},
            )
            or {}
        ),
        "derived_metrics": dict(
            split_record.get(
                "derived_metrics",
                {},
            )
            or {}
        ),
    }


# ---------------------------------------------------------------------
# Company-context warning construction
# ---------------------------------------------------------------------


def build_company_context_warnings(
    request: CompanyResearchRequest,
    company_data: Dict[str, Any],
    quantitative_data: Dict[str, Any],
    news_evidence: List[NewsEvidence],
    filing_evidence: List[FilingEvidence],
    research_result_supplied: bool,
) -> List[str]:
    """Build deterministic warnings for a standalone company context."""

    ticker = normalize_ticker(
        request.ticker
    )

    warnings = list(
        company_data.get(
            "data_warnings",
            [],
        )
        or []
    )

    metadata = company_data.get(
        "company_metadata"
    )

    if not metadata:
        warnings.append(
            f"Company metadata was unavailable for {ticker}."
        )

    if request.include_financial_history:
        if not company_data.get("financial_history"):
            warnings.append(
                "No point-in-time financial history was available for "
                f"{ticker}."
            )

    if not company_data.get("fundamental_summary"):
        warnings.append(
            f"The derived fundamental summary was unavailable for {ticker}."
        )

    if not company_data.get("market_history_summary"):
        warnings.append(
            f"The market and technical summary was unavailable for {ticker}."
        )

    if request.include_news:
        if not news_evidence:
            warnings.append(
                "No qualifying recent news evidence was found for "
                f"{ticker}."
            )
        elif not has_full_news_text(news_evidence):
            warnings.append(
                NEWS_SUMMARY_LIMITATION
            )

    if request.include_filings and not filing_evidence:
        warnings.append(
            "No qualifying supported SEC filing evidence was found for "
            f"{ticker}."
        )

    if research_result_supplied:
        if (
            not quantitative_data.get("factor_scores")
            and not quantitative_data.get("derived_metrics")
        ):
            warnings.append(
                f"{ticker} did not have a usable quantitative record in the "
                "supplied research-engine result."
            )
    else:
        warnings.append(
            "No research-engine result was supplied, so universe rank, "
            "screen rank, factor scores, and expected excess return may be "
            "unavailable."
        )

    if request.comparison_tickers:
        warnings.append(
            "Comparison tickers are included as identifiers only in the "
            "current CompanyResearchContext schema. The agent should not "
            "make detailed peer comparisons without separately supplied "
            "comparison-company evidence."
        )

    warnings.append(
        MODEL_LIMITATION
    )

    return deduplicate_messages(warnings)


# ---------------------------------------------------------------------
# Main company service
# ---------------------------------------------------------------------


def prepare_company_research_context(
    request: CompanyResearchRequest,
    research_result: Optional[Dict[str, Any]] = None,
) -> CompanyResearchContext:
    """
    Assemble deterministic context for one company-research agent.

    The service can operate without a research-engine result. Supplying one
    enriches the context with:
    - universe and screen ranks;
    - factor-category scores;
    - underlying derived metrics;
    - expected excess return;
    - current portfolio membership and weight.
    """

    if not isinstance(request, CompanyResearchRequest):
        raise TypeError(
            "request must be a CompanyResearchRequest."
        )

    clean_ticker = normalize_ticker(
        request.ticker
    )

    company_data = get_company_core_research_data(
        ticker=clean_ticker,
        as_of_date=request.as_of_date,
        financial_history_limit=(
            request.financial_history_limit
        ),
        period_mode=DEFAULT_COMPANY_PERIOD_MODE,
        refresh_if_missing=True,
        refresh_recent_data=(
            request.refresh_recent_data
        ),
    )

    financial_history = list(
        company_data.get(
            "financial_history",
            [],
        )
        or []
    )

    if not request.include_financial_history:
        financial_history = []

    # -------------------------------------------------------------
    # Company news
    # -------------------------------------------------------------

    news_evidence: List[NewsEvidence] = []

    if (
        request.include_news
        and request.max_news_articles > 0
    ):
        news_evidence = get_news_evidence(
            ticker=clean_ticker,
            as_of_date=request.as_of_date,
            days_back=request.news_days_back,
            limit=request.max_news_articles,
            refresh_if_missing=True,
            refresh_recent_data=(
                request.refresh_recent_data
            ),
            include_raw_text_excerpt=True,
        )

    # -------------------------------------------------------------
    # Company filings
    # -------------------------------------------------------------

    filing_evidence: List[FilingEvidence] = []

    if (
        request.include_filings
        and request.filing_limit > 0
    ):
        filing_evidence = get_filing_evidence(
            ticker=clean_ticker,
            as_of_date=request.as_of_date,
            form_limits=None,
            refresh_if_missing=True,
            refresh_recent_data=(
                request.refresh_recent_data
            ),
            include_excerpts=True,
        )[:request.filing_limit]

    # -------------------------------------------------------------
    # Optional quantitative and portfolio information
    # -------------------------------------------------------------

    quantitative_data = extract_company_quantitative_context(
        ticker=clean_ticker,
        research_result=research_result,
    )

    metadata = (
        company_data.get("company_metadata")
        or {}
    )

    data_warnings = build_company_context_warnings(
        request=request,
        company_data=company_data,
        quantitative_data=quantitative_data,
        news_evidence=news_evidence,
        filing_evidence=filing_evidence,
        research_result_supplied=(
            research_result is not None
        ),
    )

    return CompanyResearchContext(
        as_of_date=request.as_of_date,
        ticker=clean_ticker,
        company_name=clean_optional_text(
            metadata.get("company_name")
        ),
        sector=clean_optional_text(
            metadata.get("sector")
        ),
        industry=clean_optional_text(
            metadata.get("industry")
        ),
        exchange=clean_optional_text(
            metadata.get("exchange")
        ),
        is_current_holding=bool(
            quantitative_data.get(
                "is_current_holding",
                False,
            )
        ),
        portfolio_weight=safe_optional_float(
            quantitative_data.get(
                "portfolio_weight"
            )
        ),
        universe_rank=quantitative_data.get(
            "universe_rank"
        ),
        screen_rank=quantitative_data.get(
            "screen_rank"
        ),
        overall_score=safe_optional_float(
            quantitative_data.get(
                "overall_score"
            )
        ),
        expected_excess_return=safe_optional_float(
            quantitative_data.get(
                "expected_excess_return"
            )
        ),
        factor_scores=dict(
            quantitative_data.get(
                "factor_scores",
                {},
            )
            or {}
        ),
        derived_metrics=dict(
            quantitative_data.get(
                "derived_metrics",
                {},
            )
            or {}
        ),
        financial_history=financial_history,
        fundamental_summary=dict(
            company_data.get(
                "fundamental_summary",
                {},
            )
            or {}
        ),
        market_history_summary=dict(
            company_data.get(
                "market_history_summary",
                {},
            )
            or {}
        ),
        recent_news=news_evidence,
        recent_filings=filing_evidence,
        comparison_tickers=list(
            request.comparison_tickers
        ),
        data_warnings=data_warnings,
    )


__all__ = [
    "build_holding_research_context",
    "build_portfolio_context_from_result",
    "prepare_quarterly_research_context",
    "extract_company_quantitative_context",
    "prepare_company_research_context",
]