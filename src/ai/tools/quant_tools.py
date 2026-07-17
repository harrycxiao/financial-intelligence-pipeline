# src/ai/tools/quant_tools.py

"""
Deterministic quantitative-research tools for the AI layer.

These functions wrap the existing analytics research engine and transform
its native Pandas outputs into clean records that AI services can use to
construct validated research-context schemas.

This module does not call an LLM and does not construct final portfolio or
company research contexts. Higher-level orchestration belongs in
research_service.py.
"""

from dataclasses import asdict
from datetime import date, datetime
import math
from typing import Any, Dict, Iterable, List, Optional, Set

import numpy as np
import pandas as pd

from src.ai.schemas.research_schemas import QuarterlyResearchRequest
from src.analytics import ResearchEngineConfig, run_research_engine
from src.analytics.predictive_models import FINAL_ALPHA_COLUMN


# ---------------------------------------------------------------------
# Quantitative column definitions
# ---------------------------------------------------------------------


FACTOR_SCORE_COLUMNS = [
    "value_score",
    "growth_score",
    "quality_score",
    "financial_strength_score",
    "efficiency_score",
    "momentum_score",
    "risk_score",
    "technical_score",
]


STATISTICAL_BASE_PREDICTION_COLUMNS = {
    "ridge",
    "elastic_net",
    "bayesian_ridge",
    "huber",
    "pcr",
    "pls",
}


IDENTIFIER_COLUMNS = {
    "ticker",
}


DATE_COLUMNS = {
    "as_of_date",
    "date",
    "period_end_date",
    "filed_date",
    "start_date",
    "end_date",
}


CONTROL_COLUMNS = {
    "universe_rank",
    "screen_rank",
    "overall_score",
    FINAL_ALPHA_COLUMN,
    "statistical_expected_excess_return",
    "machine_learning_expected_excess_return",
    "combined_expected_excess_return",
} | STATISTICAL_BASE_PREDICTION_COLUMNS


EXPECTED_RESEARCH_RESULT_KEYS = {
    "as_of_date",
    "configuration",
    "universe_size",
    "eligible_universe_size",
    "eligible_tickers",
    "training_as_of_dates",
    "full_factor_scores",
    "screened_factor_scores",
    "screened_tickers",
    "selected_tickers",
    "alpha_scores",
    "selected_research",
    "portfolio_weights",
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
    """Normalize and deduplicate tickers while preserving input order."""

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
    Convert Pandas and NumPy values into normal Python values.

    Unlike the API serializer, this helper preserves date and datetime objects
    because the AI service still operates inside Python.
    """

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, np.ndarray):
        return [to_python_value(item) for item in value.tolist()]

    if isinstance(value, np.generic):
        return to_python_value(value.item())

    if isinstance(value, dict):
        return {
            str(key): to_python_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [to_python_value(item) for item in value]

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


def dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert a DataFrame into clean Python dictionaries."""

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


def coerce_records_dataframe(value: Any) -> pd.DataFrame:
    """
    Convert a DataFrame or record collection into a defensive DataFrame copy.

    This lets the tools work with both:
    - native research-engine results containing DataFrames;
    - previously serialized results containing lists of dictionaries.
    """

    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value.copy()

    if isinstance(value, list):
        if not value:
            return pd.DataFrame()

        return pd.DataFrame(value).copy()

    if isinstance(value, dict):
        if not value:
            return pd.DataFrame()

        try:
            return pd.DataFrame(value).copy()
        except ValueError:
            return pd.DataFrame([value]).copy()

    raise TypeError(
        "Expected a Pandas DataFrame, list of records, dictionary, or None."
    )


def normalize_ticker_column(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a DataFrame's ticker column when present."""

    result = df.copy()

    if "ticker" in result.columns:
        result["ticker"] = (
            result["ticker"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

    return result


# ---------------------------------------------------------------------
# Research-engine configuration and execution
# ---------------------------------------------------------------------


def build_research_engine_config(
    request: QuarterlyResearchRequest,
) -> ResearchEngineConfig:
    """
    Convert an AI-layer quarterly request into ResearchEngineConfig.

    QuarterlyResearchRequest intentionally exposes only the controls needed
    by the first AI workflow. Remaining analytics settings use the production
    defaults defined by ResearchEngineConfig.
    """

    default_config = ResearchEngineConfig()

    return ResearchEngineConfig(
        period_mode=request.period_mode,
        top_screen_n=request.top_screen_n,
        final_portfolio_n=request.final_portfolio_n,

        minimum_return_rows=default_config.minimum_return_rows,

        training_lookback_periods=(
            default_config.training_lookback_periods
        ),
        training_period_months=(
            default_config.training_period_months
        ),
        min_train_periods=default_config.min_train_periods,
        benchmark_ticker=default_config.benchmark_ticker,

        portfolio_method=request.portfolio_method,
        covariance_method=default_config.covariance_method,
        ewma_span=default_config.ewma_span,

        max_weight=default_config.max_weight,
        risk_aversion=default_config.risk_aversion,
        risk_free_signal=default_config.risk_free_signal,

        hrp_linkage_method=default_config.hrp_linkage_method,
        hrp_use_expected_return_signal=(
            default_config.hrp_use_expected_return_signal
        ),
        hrp_return_risk_metric=(
            default_config.hrp_return_risk_metric
        ),

        use_cache=request.use_cache,
    )


def validate_research_result(result: Dict[str, Any]) -> None:
    """
    Validate the high-level structure returned by run_research_engine.

    This catches analytics-interface changes before malformed data reaches
    research_service.py or an LLM agent.
    """

    if not isinstance(result, dict):
        raise TypeError(
            "run_research_engine must return a dictionary."
        )

    missing_keys = EXPECTED_RESEARCH_RESULT_KEYS - set(result.keys())

    if missing_keys:
        raise ValueError(
            "Research-engine result is missing required keys: "
            f"{sorted(missing_keys)}"
        )

    selected_tickers = normalize_ticker_list(
        result.get("selected_tickers", [])
    )

    if not selected_tickers:
        raise ValueError(
            "Research-engine result did not contain selected tickers."
        )

    weights = result.get("portfolio_weights", {})

    if not isinstance(weights, dict):
        raise TypeError(
            "Research-engine portfolio_weights must be a dictionary."
        )

    selected_research = coerce_records_dataframe(
        result.get("selected_research")
    )

    if selected_research.empty:
        raise ValueError(
            "Research-engine selected_research output is empty."
        )

    if "ticker" not in selected_research.columns:
        raise ValueError(
            "selected_research must contain a 'ticker' column."
        )

    selected_research = normalize_ticker_column(selected_research)
    available_tickers = set(selected_research["ticker"].tolist())

    missing_selected_rows = (
        set(selected_tickers) - available_tickers
    )

    if missing_selected_rows:
        raise ValueError(
            "selected_research is missing rows for selected tickers: "
            f"{sorted(missing_selected_rows)}"
        )


def run_quantitative_research(
    request: QuarterlyResearchRequest,
) -> Dict[str, Any]:
    """
    Run one complete point-in-time quantitative research workflow.

    The native result is preserved, including Pandas DataFrames, because this
    tool is used internally. JSON conversion belongs at an API boundary.
    """

    config = build_research_engine_config(request)

    result = run_research_engine(
        universe_tickers=request.universe_tickers,
        as_of_date=request.as_of_date,
        config=config,
    )

    validate_research_result(result)

    return result


def get_research_engine_configuration(
    request: QuarterlyResearchRequest,
) -> Dict[str, Any]:
    """
    Return the effective analytics configuration for a quarterly request.

    This is useful for logs, tests, and methodology information without
    requiring a complete research-engine execution.
    """

    config = build_research_engine_config(request)
    return to_python_value(asdict(config))


# ---------------------------------------------------------------------
# Selected-stock record extraction
# ---------------------------------------------------------------------


def extract_selected_research_records(
    research_result: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Return selected-stock research rows keyed by normalized ticker.

    Each record retains all factor scores, derived metrics, and the final
    statistical expected-excess-return column.
    """

    selected_tickers = normalize_ticker_list(
        research_result.get("selected_tickers", [])
    )

    selected_df = coerce_records_dataframe(
        research_result.get("selected_research")
    )

    if selected_df.empty:
        return {}

    if "ticker" not in selected_df.columns:
        raise ValueError(
            "selected_research must contain a 'ticker' column."
        )

    selected_df = normalize_ticker_column(selected_df)

    # Prefer the last row defensively if duplicated ticker rows exist.
    selected_df = selected_df.drop_duplicates(
        subset=["ticker"],
        keep="last",
    )

    selected_lookup = {}

    for record in dataframe_to_records(selected_df):
        ticker = normalize_ticker(record["ticker"])

        if selected_tickers and ticker not in selected_tickers:
            continue

        record["ticker"] = ticker
        selected_lookup[ticker] = record

    # Preserve selected-ticker order in the returned dictionary.
    ordered_lookup = {}

    for ticker in selected_tickers:
        record = selected_lookup.get(ticker)

        if record is not None:
            ordered_lookup[ticker] = record

    return ordered_lookup


def extract_portfolio_weights(
    research_result: Dict[str, Any],
) -> Dict[str, float]:
    """Normalize and validate portfolio weights from a research result."""

    raw_weights = research_result.get("portfolio_weights", {})

    if raw_weights is None:
        return {}

    if not isinstance(raw_weights, dict):
        raise TypeError("portfolio_weights must be a dictionary.")

    normalized_weights = {}

    for ticker, weight in raw_weights.items():
        clean_ticker = normalize_ticker(ticker)

        if weight is None:
            continue

        numeric_weight = float(weight)

        if not math.isfinite(numeric_weight):
            continue

        if numeric_weight < 0.0:
            raise ValueError(
                f"Negative long-only weight found for {clean_ticker}."
            )

        normalized_weights[clean_ticker] = numeric_weight

    return normalized_weights


# ---------------------------------------------------------------------
# Any-ticker lookup from a research result
# ---------------------------------------------------------------------


def merge_factor_and_alpha_records(
    factor_df: pd.DataFrame,
    alpha_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge factor rows with final alpha predictions by ticker.

    Existing alpha columns in the factor dataframe are preserved unless they
    are missing, preventing duplicate suffix columns.
    """

    factor_df = normalize_ticker_column(factor_df)
    alpha_df = normalize_ticker_column(alpha_df)

    if factor_df.empty:
        return pd.DataFrame()

    if "ticker" not in factor_df.columns:
        raise ValueError(
            "Factor-score dataframe must contain a 'ticker' column."
        )

    if alpha_df.empty:
        return factor_df

    if "ticker" not in alpha_df.columns:
        raise ValueError(
            "Alpha-score dataframe must contain a 'ticker' column."
        )

    alpha_columns = ["ticker"]

    if FINAL_ALPHA_COLUMN in alpha_df.columns:
        alpha_columns.append(FINAL_ALPHA_COLUMN)

    if (
        "statistical_expected_excess_return" in alpha_df.columns
        and "statistical_expected_excess_return" not in alpha_columns
    ):
        alpha_columns.append(
            "statistical_expected_excess_return"
        )

    if len(alpha_columns) == 1:
        return factor_df

    alpha_subset = alpha_df.loc[:, alpha_columns].copy()
    alpha_subset = alpha_subset.drop_duplicates(
        subset=["ticker"],
        keep="last",
    )

    overlapping_columns = [
        column
        for column in alpha_columns
        if column != "ticker" and column in factor_df.columns
    ]

    if overlapping_columns:
        alpha_subset = alpha_subset.drop(
            columns=overlapping_columns,
        )

    if len(alpha_subset.columns) == 1:
        return factor_df

    return factor_df.merge(
        alpha_subset,
        on="ticker",
        how="left",
    )


def get_ticker_research_record(
    research_result: Dict[str, Any],
    ticker: str,
    full_universe: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve one ticker's quantitative row from a research result.

    When full_universe is False, only selected_research is searched.

    When full_universe is True, full_factor_scores is merged with alpha_scores,
    allowing lookup of any eligible ticker included in the engine run.
    """

    clean_ticker = normalize_ticker(ticker)

    if not full_universe:
        selected_records = extract_selected_research_records(
            research_result
        )
        return selected_records.get(clean_ticker)

    factor_df = coerce_records_dataframe(
        research_result.get("full_factor_scores")
    )
    alpha_df = coerce_records_dataframe(
        research_result.get("alpha_scores")
    )

    combined_df = merge_factor_and_alpha_records(
        factor_df=factor_df,
        alpha_df=alpha_df,
    )

    if combined_df.empty or "ticker" not in combined_df.columns:
        return None

    combined_df = normalize_ticker_column(combined_df)

    ticker_rows = combined_df.loc[
        combined_df["ticker"] == clean_ticker,
        :,
    ].copy()

    if ticker_rows.empty:
        return None

    record = dataframe_to_records(ticker_rows.tail(1))[0]
    record["ticker"] = clean_ticker

    return record


# ---------------------------------------------------------------------
# Quantitative record classification
# ---------------------------------------------------------------------


def get_expected_excess_return(
    record: Dict[str, Any],
) -> Optional[float]:
    """
    Extract the preferred expected-excess-return signal from one record.

    FINAL_ALPHA_COLUMN is authoritative. The statistical model's native
    output column is accepted as a defensive fallback.
    """

    candidate_columns = [
        FINAL_ALPHA_COLUMN,
        "statistical_expected_excess_return",
        "combined_expected_excess_return",
        "machine_learning_expected_excess_return",
    ]

    for column in candidate_columns:
        value = record.get(column)

        if value is None:
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue

        if math.isfinite(numeric_value):
            return numeric_value

    return None


def get_positive_rank(
    record: Dict[str, Any],
    column: str,
) -> Optional[int]:
    """Extract one positive integer ranking from a quantitative record."""

    value = record.get(column)

    if value is None:
        return None

    try:
        numeric_rank = int(value)
    except (TypeError, ValueError):
        return None

    if numeric_rank < 1:
        return None

    return numeric_rank


def split_quantitative_record(
    record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Separate one quantitative-engine row into ranks, factor scores,
    expected alpha, and raw derived metrics.

    Company identity metadata is intentionally handled by company_tools.py.
    """

    if not isinstance(record, dict):
        raise TypeError("record must be a dictionary.")

    clean_record = {
        str(key): to_python_value(value)
        for key, value in record.items()
    }

    ticker_value = clean_record.get("ticker")

    if ticker_value is None:
        raise ValueError(
            "Quantitative research record must contain 'ticker'."
        )

    ticker = normalize_ticker(ticker_value)

    factor_scores = {}

    for column in FACTOR_SCORE_COLUMNS:
        value = clean_record.get(column)

        if value is None:
            factor_scores[column] = None
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            factor_scores[column] = None
            continue

        factor_scores[column] = (
            numeric_value
            if math.isfinite(numeric_value)
            else None
        )

    overall_score = clean_record.get("overall_score")

    if overall_score is not None:
        try:
            overall_score = float(overall_score)

            if not math.isfinite(overall_score):
                overall_score = None
        except (TypeError, ValueError):
            overall_score = None

    excluded_derived_columns = (
        IDENTIFIER_COLUMNS
        | DATE_COLUMNS
        | CONTROL_COLUMNS
        | set(FACTOR_SCORE_COLUMNS)
    )

    derived_metrics = {
        column: value
        for column, value in clean_record.items()
        if column not in excluded_derived_columns
    }

    return {
        "ticker": ticker,
        "as_of_date": clean_record.get("as_of_date"),
        "universe_rank": get_positive_rank(
            clean_record,
            "universe_rank",
        ),
        "screen_rank": get_positive_rank(
            clean_record,
            "screen_rank",
        ),
        "overall_score": overall_score,
        "expected_excess_return": get_expected_excess_return(
            clean_record
        ),
        "factor_scores": factor_scores,
        "derived_metrics": derived_metrics,
    }


def split_selected_quantitative_records(
    research_result: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Split every selected-stock row into context-ready quantitative sections.

    The result is keyed by ticker for efficient use by research_service.py.
    """

    selected_records = extract_selected_research_records(
        research_result
    )

    return {
        ticker: split_quantitative_record(record)
        for ticker, record in selected_records.items()
    }


# ---------------------------------------------------------------------
# Compact deterministic summaries
# ---------------------------------------------------------------------


def summarize_quantitative_research(
    research_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a compact summary of one research-engine result.

    Useful for logs, tests, system prompts, and portfolio-level context.
    Full DataFrames are intentionally excluded.
    """

    selected_tickers = normalize_ticker_list(
        research_result.get("selected_tickers", [])
    )

    screened_tickers = normalize_ticker_list(
        research_result.get("screened_tickers", [])
    )

    eligible_tickers = normalize_ticker_list(
        research_result.get("eligible_tickers", [])
    )

    return {
        "as_of_date": to_python_value(
            research_result.get("as_of_date")
        ),
        "configuration": to_python_value(
            research_result.get("configuration", {})
        ),
        "universe_size": int(
            research_result.get("universe_size", 0) or 0
        ),
        "eligible_universe_size": int(
            research_result.get(
                "eligible_universe_size",
                len(eligible_tickers),
            )
            or 0
        ),
        "eligible_ticker_count": len(eligible_tickers),
        "screened_ticker_count": len(screened_tickers),
        "selected_ticker_count": len(selected_tickers),
        "screened_tickers": screened_tickers,
        "selected_tickers": selected_tickers,
        "portfolio_weights": extract_portfolio_weights(
            research_result
        ),
        "training_as_of_dates": to_python_value(
            research_result.get("training_as_of_dates", [])
        ),
    }


__all__ = [
    "FACTOR_SCORE_COLUMNS",
    "build_research_engine_config",
    "validate_research_result",
    "run_quantitative_research",
    "get_research_engine_configuration",
    "extract_selected_research_records",
    "extract_portfolio_weights",
    "merge_factor_and_alpha_records",
    "get_ticker_research_record",
    "get_expected_excess_return",
    "get_positive_rank",
    "split_quantitative_record",
    "split_selected_quantitative_records",
    "summarize_quantitative_research",
    "STATISTICAL_BASE_PREDICTION_COLUMNS",
]