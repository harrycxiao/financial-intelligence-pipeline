# src/ai/tools/filing_tools.py

"""
Deterministic SEC-filing tools for the AI layer.

These functions:
- fetch and store recent 10-K, 10-Q, and 8-K filings;
- retrieve filings from the database using point-in-time filtering;
- extract compact, relevant excerpts from stored filing text;
- construct validated FilingEvidence objects for research contexts.

This module does not:
- calculate fundamental ratios;
- call an LLM;
- generate filing summaries;
- construct HoldingResearchContext or CompanyResearchContext;
- produce investment conclusions.

Higher-level orchestration belongs in research_service.py.
"""

from datetime import date, datetime
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.ai.schemas.research_schemas import FilingEvidence
from src.ai.tools.company_tools import ensure_company_metadata
from src.database import query, store_sec_filings
from src.ingestion import fetch_sec_filings


# ---------------------------------------------------------------------
# Filing configuration
# ---------------------------------------------------------------------


SUPPORTED_FILING_TYPES = {
    "10-K",
    "10-Q",
    "8-K",
}


# Broader evidence defaults for a dedicated company-research report.
DEFAULT_RESEARCH_FORM_LIMITS = {
    "8-K": 5,
    "10-Q": 2,
    "10-K": 1,
}


# Smaller context for each stock in a multi-holding portfolio report.
DEFAULT_HOLDING_FORM_LIMITS = {
    "8-K": 3,
    "10-Q": 1,
    "10-K": 1,
}


# Routine refresh limits. These determine how many filings are downloaded,
# not necessarily how many are ultimately supplied to the LLM.
DEFAULT_REFRESH_FORM_LIMITS = {
    "8-K": 8,
    "10-Q": 2,
    "10-K": 1,
}


DEFAULT_EXCERPT_CHARACTER_LIMITS = {
    "8-K": 12000,
    "10-Q": 10000,
    "10-K": 8000,
}


DEFAULT_MAX_CHARACTERS_PER_SECTION = {
    "8-K": 4000,
    "10-Q": 3000,
    "10-K": 2500,
}


# Section phrases are ordered approximately by research usefulness.
FILING_SECTION_KEYWORDS = {
    "8-K": [
        "item 1.01",
        "entry into a material definitive agreement",
        "item 1.02",
        "termination of a material definitive agreement",
        "item 2.01",
        "completion of acquisition or disposition of assets",
        "item 2.02",
        "results of operations and financial condition",
        "item 2.05",
        "costs associated with exit or disposal activities",
        "item 2.06",
        "material impairments",
        "item 3.01",
        "notice of delisting",
        "item 5.02",
        "departure of directors or certain officers",
        "appointment of certain officers",
        "item 5.07",
        "submission of matters to a vote of security holders",
        "item 7.01",
        "regulation fd disclosure",
        "item 8.01",
        "other events",
        "item 9.01",
        "financial statements and exhibits",
        "earnings release",
        "financial results",
        "guidance",
        "acquisition",
        "disposition",
        "restructuring",
        "impairment",
    ],
    "10-Q": [
        "item 2. management's discussion and analysis",
        "item 2. management’s discussion and analysis",
        "item 3. quantitative and qualitative disclosures about market risk",
        "item 4. controls and procedures",
        "item 1a. risk factors",
        "management's discussion and analysis",
        "management’s discussion and analysis",
        "results of operations",
        "liquidity and capital resources",
        "critical accounting estimates",
        "risk factors",
        "quantitative and qualitative disclosures about market risk",
        "controls and procedures",
        "legal proceedings",
        "unregistered sales of equity securities",
    ],
    "10-K": [
        "item 1. business",
        "item 1a. risk factors",
        "item 3. legal proceedings",
        "item 7. management's discussion and analysis",
        "item 7. management’s discussion and analysis",
        "item 7a. quantitative and qualitative disclosures about market risk",
        "item 9a. controls and procedures",
        "business",
        "risk factors",
        "unresolved staff comments",
        "properties",
        "legal proceedings",
        "management's discussion and analysis",
        "management’s discussion and analysis",
        "results of operations",
        "liquidity and capital resources",
        "critical accounting estimates",
        "quantitative and qualitative disclosures about market risk",
        "controls and procedures",
        "market for registrant's common equity",
        "market for registrant’s common equity",
    ],
}


FILING_INTERNAL_COLUMNS = {
    "filing_id",
    "company_id",
    "created_at",
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


def normalize_filing_type(filing_type: str) -> str:
    """Normalize and validate one supported SEC filing type."""

    clean_filing_type = str(filing_type).upper().strip()

    if clean_filing_type not in SUPPORTED_FILING_TYPES:
        raise ValueError(
            "filing_type must be one of: "
            f"{sorted(SUPPORTED_FILING_TYPES)}."
        )

    return clean_filing_type


def normalize_filing_types(
    filing_types: Optional[Iterable[str]],
) -> Optional[List[str]]:
    """Normalize and deduplicate an optional filing-type collection."""

    if filing_types is None:
        return None

    normalized = []
    seen = set()

    for filing_type in filing_types:
        clean_filing_type = normalize_filing_type(filing_type)

        if clean_filing_type in seen:
            continue

        seen.add(clean_filing_type)
        normalized.append(clean_filing_type)

    return normalized


def normalize_form_limits(
    form_limits: Optional[Dict[str, int]],
    defaults: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """
    Normalize per-form filing limits.

    Missing supported forms default to zero when a custom dictionary is
    supplied. When form_limits is None, the provided defaults are used.
    """

    source_limits = (
        dict(defaults or DEFAULT_RESEARCH_FORM_LIMITS)
        if form_limits is None
        else dict(form_limits)
    )

    normalized = {
        filing_type: 0
        for filing_type in SUPPORTED_FILING_TYPES
    }

    for filing_type, limit in source_limits.items():
        clean_filing_type = normalize_filing_type(filing_type)

        try:
            numeric_limit = int(limit)
        except (TypeError, ValueError):
            raise ValueError(
                f"Filing limit for {clean_filing_type} must be an integer."
            )

        if numeric_limit < 0:
            raise ValueError(
                f"Filing limit for {clean_filing_type} cannot be negative."
            )

        normalized[clean_filing_type] = numeric_limit

    return normalized


def normalize_accession_number(accession_number: str) -> str:
    """Normalize and validate one SEC accession number."""

    clean_accession_number = str(accession_number).strip()

    if not clean_accession_number:
        raise ValueError("accession_number cannot be empty.")

    return clean_accession_number


def to_python_value(value: Any) -> Any:
    """Convert Pandas and NumPy values into ordinary Python values."""

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


def coerce_optional_date(value: Any) -> Optional[date]:
    """Convert a database or serialized value into an optional date."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    parsed_value = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed_value):
        return None

    if isinstance(parsed_value, pd.Timestamp):
        return parsed_value.date()

    return None


# ---------------------------------------------------------------------
# Filing-record cleaning
# ---------------------------------------------------------------------


def clean_filing_text(raw_text: Optional[str]) -> Optional[str]:
    """
    Perform final whitespace cleanup on stored filing text.

    HTML removal already occurs during SEC ingestion, so this function avoids
    unnecessary parsing and only normalizes whitespace.
    """

    if raw_text is None:
        return None

    clean_text = re.sub(
        r"\s+",
        " ",
        str(raw_text),
    ).strip()

    if not clean_text:
        return None

    return clean_text


def clean_optional_text(value: Any) -> Optional[str]:
    """Return a stripped string or None for an empty value."""

    if value is None:
        return None

    clean_value = str(value).strip()

    if not clean_value:
        return None

    return clean_value


def clean_filing_record(
    ticker: str,
    filing: Dict[str, Any],
    include_raw_text: bool = False,
) -> Dict[str, Any]:
    """
    Convert one stored filing dictionary into the AI-layer record format.

    Query-layer internal IDs and timestamps are removed, and ticker is added
    explicitly because filing query dictionaries are keyed through company_id.
    """

    if not isinstance(filing, dict):
        raise TypeError("filing must be a dictionary.")

    clean_ticker = normalize_ticker(ticker)

    filing_type_value = filing.get("filing_type")

    if filing_type_value is None:
        raise ValueError("Filing record must contain filing_type.")

    filing_type = normalize_filing_type(filing_type_value)

    result = {
        "ticker": clean_ticker,
        "filing_type": filing_type,
        "filing_date": coerce_optional_date(
            filing.get("filing_date")
        ),
        "accession_number": clean_optional_text(
            filing.get("accession_number")
        ),
        "filing_url": clean_optional_text(
            filing.get("filing_url")
        ),
        "summary": clean_optional_text(
            filing.get("summary")
        ),
    }

    if include_raw_text:
        result["raw_text"] = clean_filing_text(
            filing.get("raw_text")
        )

    return result


# ---------------------------------------------------------------------
# Refresh and persistence
# ---------------------------------------------------------------------


def refresh_company_filings(
    ticker: str,
    form_limits: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Fetch and store recent SEC filings for one company.

    The refresh limits determine how many filings are downloaded from each
    supported form. Existing accession numbers are handled by the persistence
    layer rather than duplicated.
    """

    clean_ticker = normalize_ticker(ticker)

    normalized_limits = normalize_form_limits(
        form_limits=form_limits,
        defaults=DEFAULT_REFRESH_FORM_LIMITS,
    )

    ensure_company_metadata(clean_ticker)

    stored_before = query.get_sec_filings(
        clean_ticker,
        include_raw_text=False,
    )
    count_before = len(stored_before)

    before_accessions = {
        filing.get("accession_number")
        for filing in stored_before
        if filing.get("accession_number")
    }

    filing_df = fetch_sec_filings(
        ticker=clean_ticker,
        form_limits=normalized_limits,
    )

    store_sec_filings(
        clean_ticker,
        filing_df,
    )

    stored_after = query.get_sec_filings(
        clean_ticker,
        include_raw_text=False,
    )
    count_after = len(stored_after)

    new_filings = [
        filing
        for filing in stored_after
        if filing.get("accession_number") not in before_accessions
    ]

    new_filings_by_type = {
        filing_type: 0
        for filing_type in SUPPORTED_FILING_TYPES
    }

    for filing in new_filings:
        filing_type = filing.get("filing_type")

        if filing_type in new_filings_by_type:
            new_filings_by_type[filing_type] += 1

    filings_by_type = {
        filing_type: 0
        for filing_type in SUPPORTED_FILING_TYPES
    }

    if filing_df is not None and not filing_df.empty:
        if "filing_type" in filing_df.columns:
            normalized_types = (
                filing_df["filing_type"]
                .astype(str)
                .str.upper()
                .str.strip()
            )

            type_counts = normalized_types.value_counts()

            for filing_type in SUPPORTED_FILING_TYPES:
                filings_by_type[filing_type] = int(
                    type_counts.get(filing_type, 0)
                )

    return {
        "ticker": clean_ticker,
        "rows_fetched": int(len(filing_df)),
        "stored_count_before": int(count_before),
        "stored_count_after": int(count_after),
        "new_rows_added": int(max(count_after - count_before, 0)),
        "filings_fetched_by_type": filings_by_type,
        "new_filings_by_type": new_filings_by_type,
        "form_limits": normalized_limits,
    }


# ---------------------------------------------------------------------
# Point-in-time filing retrieval
# ---------------------------------------------------------------------


def get_company_filings(
    ticker: str,
    as_of_date: date,
    filing_types: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
    include_raw_text: bool = False,
) -> List[Dict[str, Any]]:
    """
    Retrieve stored SEC filings available by a requested as-of date.

    Results are sorted newest first. Historical reports therefore do not
    receive filings published after their requested research date.
    """

    clean_ticker = normalize_ticker(ticker)
    normalized_types = normalize_filing_types(filing_types)

    if limit is not None and limit < 0:
        raise ValueError("limit cannot be negative.")

    raw_filings = query.get_sec_filings(
        clean_ticker,
        include_raw_text=include_raw_text,
    )

    cleaned_filings = []

    for filing in raw_filings:
        clean_filing = clean_filing_record(
            ticker=clean_ticker,
            filing=filing,
            include_raw_text=include_raw_text,
        )

        filing_date = clean_filing.get("filing_date")

        if filing_date is None:
            continue

        if filing_date > as_of_date:
            continue

        if (
            normalized_types is not None
            and clean_filing["filing_type"] not in normalized_types
        ):
            continue

        cleaned_filings.append(clean_filing)

    cleaned_filings.sort(
        key=lambda item: item.get("filing_date") or date.min,
        reverse=True,
    )

    if limit is not None:
        cleaned_filings = cleaned_filings[:limit]

    return cleaned_filings


def get_company_filings_by_type(
    ticker: str,
    filing_type: str,
    as_of_date: date,
    limit: int = 5,
    include_raw_text: bool = False,
) -> List[Dict[str, Any]]:
    """Retrieve point-in-time filings for one specified SEC form."""

    if limit < 0:
        raise ValueError("limit cannot be negative.")

    clean_filing_type = normalize_filing_type(filing_type)

    return get_company_filings(
        ticker=ticker,
        as_of_date=as_of_date,
        filing_types=[clean_filing_type],
        limit=limit,
        include_raw_text=include_raw_text,
    )


def get_latest_company_filing(
    ticker: str,
    as_of_date: date,
    filing_type: Optional[str] = None,
    include_raw_text: bool = False,
) -> Optional[Dict[str, Any]]:
    """Retrieve the latest qualifying filing available by an as-of date."""

    filing_types = None

    if filing_type is not None:
        filing_types = [
            normalize_filing_type(filing_type)
        ]

    filings = get_company_filings(
        ticker=ticker,
        as_of_date=as_of_date,
        filing_types=filing_types,
        limit=1,
        include_raw_text=include_raw_text,
    )

    if not filings:
        return None

    return filings[0]


def get_filing_by_accession(
    accession_number: str,
    include_raw_text: bool = True,
) -> Optional[Dict[str, Any]]:
    """Retrieve one filing by its globally unique accession number."""

    clean_accession_number = normalize_accession_number(
        accession_number
    )

    filing = query.get_filing_by_accession_number(
        accession_number=clean_accession_number,
        include_raw_text=include_raw_text,
    )

    if filing is None:
        return None

    company_id = filing.get("company_id")

    if company_id is None:
        return None

    company = query.get_company_by_id(int(company_id))

    if company is None:
        return None

    return clean_filing_record(
        ticker=company["ticker"],
        filing=filing,
        include_raw_text=include_raw_text,
    )


# ---------------------------------------------------------------------
# Filing selection
# ---------------------------------------------------------------------


def select_filings_by_form_limits(
    filings: Sequence[Dict[str, Any]],
    form_limits: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """
    Select the newest requested number of filings for each supported form.

    The final result is ordered by filing date rather than grouped by form.
    """

    normalized_limits = normalize_form_limits(
        form_limits=form_limits,
        defaults=DEFAULT_RESEARCH_FORM_LIMITS,
    )

    counts = {
        filing_type: 0
        for filing_type in SUPPORTED_FILING_TYPES
    }

    sorted_filings = sorted(
        filings,
        key=lambda item: (
            coerce_optional_date(item.get("filing_date"))
            or date.min
        ),
        reverse=True,
    )

    selected = []

    for filing in sorted_filings:
        filing_type_value = filing.get("filing_type")

        if filing_type_value is None:
            continue

        try:
            filing_type = normalize_filing_type(
                filing_type_value
            )
        except ValueError:
            continue

        allowed_count = normalized_limits.get(
            filing_type,
            0,
        )

        if allowed_count <= 0:
            continue

        if counts[filing_type] >= allowed_count:
            continue

        selected.append(filing)
        counts[filing_type] += 1

        if all(
            counts[form_type] >= normalized_limits[form_type]
            for form_type in SUPPORTED_FILING_TYPES
        ):
            break

    selected.sort(
        key=lambda item: (
            coerce_optional_date(item.get("filing_date"))
            or date.min
        ),
        reverse=True,
    )

    return selected


# ---------------------------------------------------------------------
# Relevant-text extraction
# ---------------------------------------------------------------------


def truncate_text(
    text: Optional[str],
    max_characters: int,
) -> Optional[str]:
    """Truncate cleaned text without returning an empty string."""

    if text is None:
        return None

    if max_characters < 1:
        raise ValueError(
            "max_characters must be at least 1."
        )

    clean_text = clean_filing_text(text)

    if clean_text is None:
        return None

    if len(clean_text) <= max_characters:
        return clean_text

    truncated = clean_text[:max_characters]

    # Avoid ending in the middle of a word when practical.
    final_space = truncated.rfind(" ")

    if final_space >= int(max_characters * 0.8):
        truncated = truncated[:final_space]

    return truncated.rstrip() + " ..."


def find_keyword_windows(
    text: str,
    keywords: Sequence[str],
    characters_before: int = 400,
    characters_after: int = 2400,
    max_matches_per_keyword: int = 2,
) -> List[Tuple[int, int]]:
    """
    Find character windows surrounding relevant filing-section phrases.

    Multiple occurrences are allowed because filings may repeat headings in
    a table of contents and again in the substantive section.
    """

    if characters_before < 0:
        raise ValueError(
            "characters_before cannot be negative."
        )

    if characters_after < 1:
        raise ValueError(
            "characters_after must be at least 1."
        )

    if max_matches_per_keyword < 1:
        raise ValueError(
            "max_matches_per_keyword must be at least 1."
        )

    lower_text = text.lower()
    windows = []

    for keyword in keywords:
        lower_keyword = keyword.lower()
        search_start = 0
        match_count = 0

        while match_count < max_matches_per_keyword:
            match_index = lower_text.find(
                lower_keyword,
                search_start,
            )

            if match_index < 0:
                break

            window_start = max(
                match_index - characters_before,
                0,
            )
            window_end = min(
                match_index
                + len(lower_keyword)
                + characters_after,
                len(text),
            )

            windows.append(
                (window_start, window_end)
            )

            search_start = match_index + len(lower_keyword)
            match_count += 1

    return windows


def merge_overlapping_windows(
    windows: Sequence[Tuple[int, int]],
    merge_gap: int = 300,
) -> List[Tuple[int, int]]:
    """
    Merge overlapping or nearby excerpt windows.

    Nearby windows are combined so repeated section keywords do not produce
    heavily duplicated text.
    """

    if merge_gap < 0:
        raise ValueError("merge_gap cannot be negative.")

    if not windows:
        return []

    sorted_windows = sorted(
        windows,
        key=lambda item: item[0],
    )

    merged = [
        sorted_windows[0]
    ]

    for current_start, current_end in sorted_windows[1:]:
        previous_start, previous_end = merged[-1]

        if current_start <= previous_end + merge_gap:
            merged[-1] = (
                previous_start,
                max(previous_end, current_end),
            )
        else:
            merged.append(
                (current_start, current_end)
            )

    return merged


def extract_windows_from_text(
    text: str,
    windows: Sequence[Tuple[int, int]],
    max_characters_per_section: Optional[int] = None,
) -> List[str]:
    """
    Extract and clean text represented by character windows.

    When max_characters_per_section is supplied, each extracted section is
    capped before the sections are stitched together. This prevents one early
    section from consuming the entire final excerpt budget.
    """

    if (
        max_characters_per_section is not None
        and max_characters_per_section < 1
    ):
        raise ValueError(
            "max_characters_per_section must be at least 1."
        )

    excerpts = []

    for start_index, end_index in windows:
        section = text[start_index:end_index].strip()

        if not section:
            continue

        # Avoid beginning in the middle of a word.
        if start_index > 0:
            first_space = section.find(" ")

            if 0 <= first_space <= 80:
                section = section[first_space + 1:]

        # Prefer ending at a nearby sentence or word boundary.
        if end_index < len(text):
            last_period = section.rfind(".")
            last_space = section.rfind(" ")

            if last_period >= int(len(section) * 0.75):
                section = section[:last_period + 1]
            elif last_space >= int(len(section) * 0.85):
                section = section[:last_space]

        section = clean_filing_text(section)

        if section is None:
            continue

        if max_characters_per_section is not None:
            section = truncate_text(
                text=section,
                max_characters=max_characters_per_section,
            )

        if section:
            excerpts.append(section)

    return excerpts


def extract_relevant_filing_excerpt(
    filing: Dict[str, Any],
    max_characters: Optional[int] = None,
) -> Optional[str]:
    """
    Build a compact relevant excerpt from one filing's stored full text.

    The extractor finds research-relevant section phrases, captures text
    surrounding those phrases, merges overlapping windows, and joins the
    resulting standalone sections.

    When no useful section phrase is found, the beginning of the filing is
    returned as a deterministic fallback.
    """

    if not isinstance(filing, dict):
        raise TypeError("filing must be a dictionary.")

    filing_type_value = filing.get("filing_type")

    if filing_type_value is None:
        raise ValueError(
            "filing must contain filing_type."
        )

    filing_type = normalize_filing_type(
        filing_type_value
    )

    raw_text = clean_filing_text(
        filing.get("raw_text")
    )

    if raw_text is None:
        return None

    character_limit = (
        DEFAULT_EXCERPT_CHARACTER_LIMITS[filing_type]
        if max_characters is None
        else int(max_characters)
    )

    if character_limit < 1:
        raise ValueError(
            "max_characters must be at least 1."
        )

    keywords = FILING_SECTION_KEYWORDS.get(
        filing_type,
        [],
    )

    if filing_type == "8-K":
        characters_before = 300
        characters_after = 2200
        max_matches_per_keyword = 2
    elif filing_type == "10-Q":
        characters_before = 500
        characters_after = 2800
        max_matches_per_keyword = 2
    else:
        characters_before = 500
        characters_after = 2600
        max_matches_per_keyword = 2

    windows = find_keyword_windows(
        text=raw_text,
        keywords=keywords,
        characters_before=characters_before,
        characters_after=characters_after,
        max_matches_per_keyword=max_matches_per_keyword,
    )

    merged_windows = merge_overlapping_windows(
        windows=windows,
        merge_gap=350,
    )

    separator = "\n\n---\n\n"

    if merged_windows:
        separator_characters = (
            len(separator) * (len(merged_windows) - 1)
        )

        available_section_characters = max(
            character_limit - separator_characters,
            1,
        )

        equal_section_budget = max(
            available_section_characters // len(merged_windows),
            1,
        )

        max_characters_per_section = min(
            DEFAULT_MAX_CHARACTERS_PER_SECTION[filing_type],
            equal_section_budget,
        )
    else:
        max_characters_per_section = (
            DEFAULT_MAX_CHARACTERS_PER_SECTION[filing_type]
        )

    excerpts = extract_windows_from_text(
        text=raw_text,
        windows=merged_windows,
        max_characters_per_section=max_characters_per_section,
    )

    if not excerpts:
        return truncate_text(
            text=raw_text,
            max_characters=character_limit,
        )

    stitched_excerpt = separator.join(excerpts)

    return truncate_text(
        text=stitched_excerpt,
        max_characters=character_limit,
    )


# ---------------------------------------------------------------------
# FilingEvidence construction
# ---------------------------------------------------------------------


def build_filing_evidence(
    ticker: str,
    filing: Dict[str, Any],
    include_excerpt: bool = True,
    max_excerpt_characters: Optional[int] = None,
) -> FilingEvidence:
    """
    Convert one clean filing record into a validated FilingEvidence object.

    The tool does not create an LLM-generated filing summary. Any existing
    stored summary is preserved, while relevant_excerpt is produced through
    deterministic text extraction.
    """

    clean_ticker = normalize_ticker(ticker)

    filing_type_value = filing.get("filing_type")

    if filing_type_value is None:
        raise ValueError(
            "filing must contain filing_type."
        )

    filing_type = normalize_filing_type(
        filing_type_value
    )

    relevant_excerpt = None

    if include_excerpt:
        relevant_excerpt = extract_relevant_filing_excerpt(
            filing=filing,
            max_characters=max_excerpt_characters,
        )

    return FilingEvidence(
        ticker=clean_ticker,
        filing_type=filing_type,
        filing_date=coerce_optional_date(
            filing.get("filing_date")
        ),
        accession_number=clean_optional_text(
            filing.get("accession_number")
        ),
        filing_url=clean_optional_text(
            filing.get("filing_url")
        ),
        summary=clean_optional_text(
            filing.get("summary")
        ),
        relevant_excerpt=relevant_excerpt,
    )


def get_filing_evidence(
    ticker: str,
    as_of_date: date,
    form_limits: Optional[Dict[str, int]] = None,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = True,
    include_excerpts: bool = True,
    max_excerpt_characters: Optional[int] = None,
) -> List[FilingEvidence]:
    """
    Retrieve filing evidence for one company.

    refresh_if_missing fetches filings only when none are stored.

    refresh_recent_data performs a current SEC refresh even when filings
    already exist. It should normally remain False for historical research.
    """

    clean_ticker = normalize_ticker(ticker)

    normalized_limits = normalize_form_limits(
        form_limits=form_limits,
        defaults=DEFAULT_RESEARCH_FORM_LIMITS,
    )

    stored_filings = query.get_sec_filings(
        clean_ticker,
        include_raw_text=False,
    )

    if refresh_recent_data:
        refresh_company_filings(
            ticker=clean_ticker,
            form_limits=DEFAULT_REFRESH_FORM_LIMITS,
        )
    elif refresh_if_missing and not stored_filings:
        refresh_company_filings(
            ticker=clean_ticker,
            form_limits=DEFAULT_REFRESH_FORM_LIMITS,
        )

    point_in_time_filings = get_company_filings(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        filing_types=SUPPORTED_FILING_TYPES,
        limit=None,
        include_raw_text=include_excerpts,
    )

    selected_filings = select_filings_by_form_limits(
        filings=point_in_time_filings,
        form_limits=normalized_limits,
    )

    evidence = []

    for filing in selected_filings:
        evidence.append(
            build_filing_evidence(
                ticker=clean_ticker,
                filing=filing,
                include_excerpt=include_excerpts,
                max_excerpt_characters=(
                    max_excerpt_characters
                ),
            )
        )

    return evidence


def get_holding_filing_evidence(
    ticker: str,
    as_of_date: date,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = True,
    include_excerpts: bool = True,
) -> List[FilingEvidence]:
    """
    Retrieve the smaller default filing set used for one portfolio holding.
    """

    return get_filing_evidence(
        ticker=ticker,
        as_of_date=as_of_date,
        form_limits=DEFAULT_HOLDING_FORM_LIMITS,
        refresh_if_missing=refresh_if_missing,
        refresh_recent_data=refresh_recent_data,
        include_excerpts=include_excerpts,
    )


def get_filing_evidence_for_tickers(
    tickers: Iterable[str],
    as_of_date: date,
    form_limits: Optional[Dict[str, int]] = None,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = True,
    include_excerpts: bool = True,
    max_excerpt_characters: Optional[int] = None,
) -> Dict[str, List[FilingEvidence]]:
    """
    Retrieve filing evidence for multiple companies.

    Errors are isolated by ticker so one SEC or database failure does not
    prevent evidence retrieval for the remaining companies.
    """

    clean_tickers = normalize_ticker_list(tickers)
    results = {}

    for ticker in clean_tickers:
        try:
            results[ticker] = get_filing_evidence(
                ticker=ticker,
                as_of_date=as_of_date,
                form_limits=form_limits,
                refresh_if_missing=refresh_if_missing,
                refresh_recent_data=refresh_recent_data,
                include_excerpts=include_excerpts,
                max_excerpt_characters=(
                    max_excerpt_characters
                ),
            )
        except Exception:
            results[ticker] = []

    return results


def get_holding_filing_evidence_for_tickers(
    tickers: Iterable[str],
    as_of_date: date,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = True,
    include_excerpts: bool = True,
) -> Dict[str, List[FilingEvidence]]:
    """
    Retrieve the compact portfolio-holding filing set for multiple tickers.
    """

    return get_filing_evidence_for_tickers(
        tickers=tickers,
        as_of_date=as_of_date,
        form_limits=DEFAULT_HOLDING_FORM_LIMITS,
        refresh_if_missing=refresh_if_missing,
        refresh_recent_data=refresh_recent_data,
        include_excerpts=include_excerpts,
    )


__all__ = [
    "SUPPORTED_FILING_TYPES",
    "DEFAULT_RESEARCH_FORM_LIMITS",
    "DEFAULT_HOLDING_FORM_LIMITS",
    "DEFAULT_REFRESH_FORM_LIMITS",
    "DEFAULT_EXCERPT_CHARACTER_LIMITS",
    "DEFAULT_MAX_CHARACTERS_PER_SECTION",
    "normalize_filing_type",
    "normalize_form_limits",
    "refresh_company_filings",
    "get_company_filings",
    "get_company_filings_by_type",
    "get_latest_company_filing",
    "get_filing_by_accession",
    "select_filings_by_form_limits",
    "clean_filing_text",
    "truncate_text",
    "find_keyword_windows",
    "merge_overlapping_windows",
    "extract_relevant_filing_excerpt",
    "build_filing_evidence",
    "get_filing_evidence",
    "get_holding_filing_evidence",
    "get_filing_evidence_for_tickers",
    "get_holding_filing_evidence_for_tickers",
]