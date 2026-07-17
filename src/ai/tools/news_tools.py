# src/ai/tools/news_tools.py

"""
Deterministic company-news tools for the AI layer.

These functions:
- fetch and store recent Finnhub company news;
- retrieve stored articles with point-in-time filtering;
- clean and normalize news records;
- rank articles for company relevance and materiality;
- reduce duplicate coverage of the same event;
- construct validated NewsEvidence objects;
- support both company-research and portfolio-holding contexts.

Version-one limitation:
Finnhub generally supplies short summaries rather than complete article text.
This module does not automatically scrape publisher pages because those pages
may involve redirects, JavaScript, paywalls, robots restrictions, or highly
variable HTML. If raw article text is stored later, this module can expose a
bounded excerpt through NewsEvidence.raw_text_excerpt.

This module does not:
- call an LLM;
- claim to have read article bodies that were not stored;
- generate investment conclusions;
- perform embedding or sentiment-model inference;
- construct complete holding, portfolio, or company research contexts.

Higher-level orchestration belongs in research_service.py.
"""

from datetime import date, datetime, time, timedelta, timezone
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import numpy as np
import pandas as pd

from src.ai.schemas.research_schemas import NewsEvidence
from src.ai.tools.company_tools import ensure_company_metadata
from src.database import query, store_news_articles
from src.ingestion import fetch_news_articles


# ---------------------------------------------------------------------
# News configuration
# ---------------------------------------------------------------------


# Broader evidence window for a dedicated single-company research report.
DEFAULT_RESEARCH_NEWS_DAYS_BACK = 90
DEFAULT_RESEARCH_NEWS_LIMIT = 12


# Smaller evidence window for each stock in a multi-holding portfolio.
DEFAULT_HOLDING_NEWS_DAYS_BACK = 30
DEFAULT_HOLDING_NEWS_LIMIT = 6


# Routine Finnhub refresh retrieves more records than the agent receives.
DEFAULT_REFRESH_NEWS_DAYS_BACK = 120
DEFAULT_REFRESH_MAX_ARTICLES = 100


# Used only when raw article text becomes available in the database.
DEFAULT_RAW_TEXT_EXCERPT_CHARACTERS = 4_000


# Minimum score normally required for an article to enter the evidence set.
DEFAULT_MINIMUM_RELEVANCE_SCORE = 2.0


# Articles with title-token similarity above this level are treated as likely
# coverage of the same event.
DEFAULT_DUPLICATE_TITLE_SIMILARITY = 0.68


NEWS_INTERNAL_COLUMNS = {
    "news_article_id",
    "company_id",
    "created_at",
}


# Words and phrases associated with potentially material company developments.
NEWS_MATERIAL_KEYWORDS = [
    "earnings",
    "financial results",
    "revenue",
    "sales",
    "profit",
    "loss",
    "margin",
    "guidance",
    "forecast",
    "outlook",
    "acquisition",
    "acquire",
    "merger",
    "partnership",
    "joint venture",
    "contract",
    "agreement",
    "customer",
    "supplier",
    "product launch",
    "launches",
    "regulatory",
    "regulator",
    "investigation",
    "lawsuit",
    "litigation",
    "antitrust",
    "recall",
    "tariff",
    "supply shortage",
    "supply chain",
    "price increase",
    "chief executive",
    "ceo",
    "chief financial officer",
    "cfo",
    "resignation",
    "appointment",
    "layoff",
    "job cuts",
    "restructuring",
    "impairment",
    "bankruptcy",
    "dividend",
    "share repurchase",
    "stock buyback",
    "capital expenditure",
    "investment",
    "data breach",
    "cyberattack",
    "approval",
    "rejection",
]


# These phrases often indicate generic, promotional, or portfolio-list content.
# They are penalties rather than hard exclusions.
NEWS_LOW_RELEVANCE_PHRASES = [
    "stocks to buy",
    "best stocks",
    "top stocks",
    "reasons to buy",
    "millionaire maker",
    "make $100k",
    "six figures",
    "retire",
    "retirement portfolio",
    "my portfolio",
    "model portfolio",
    "etf",
    "exchange-traded fund",
    "fund that",
    "stock prediction",
    "price prediction",
    "magnificent seven",
    "could make you rich",
    "buy and hold forever",
    "passive income",
]


# Common words removed before title-similarity comparison.
TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "will",
    "with",
    "why",
    "what",
    "how",
    "after",
    "before",
    "amid",
    "says",
    "said",
    "stock",
    "shares",
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


def clean_optional_text(value: Any) -> Optional[str]:
    """Return a stripped string or None for an empty value."""

    if value is None:
        return None

    clean_value = re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()

    if not clean_value:
        return None

    return clean_value


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


def coerce_optional_datetime(
    value: Any,
) -> Optional[datetime]:
    """
    Convert a supported value into a timezone-aware UTC datetime.

    Naive datetimes are interpreted as UTC because Finnhub timestamps are
    supplied in UTC and your ingestion function explicitly uses utc=True.
    """

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        parsed_value = value.to_pydatetime()
    elif isinstance(value, datetime):
        parsed_value = value
    elif isinstance(value, date):
        parsed_value = datetime.combine(
            value,
            time.min,
        )
    else:
        parsed_timestamp = pd.to_datetime(
            value,
            errors="coerce",
            utc=True,
        )

        if pd.isna(parsed_timestamp):
            return None

        if not isinstance(parsed_timestamp, pd.Timestamp):
            return None

        parsed_value = parsed_timestamp.to_pydatetime()

    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(
            tzinfo=timezone.utc,
        )
    else:
        parsed_value = parsed_value.astimezone(
            timezone.utc,
        )

    return parsed_value


def get_as_of_datetime(as_of_date: date) -> datetime:
    """Return the inclusive UTC endpoint for one as-of date."""

    return datetime.combine(
        as_of_date,
        time.max,
        tzinfo=timezone.utc,
    )


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalize a URL for storage comparison and evidence output."""

    clean_url = clean_optional_text(url)

    if clean_url is None:
        return None

    return clean_url


# ---------------------------------------------------------------------
# News-record cleaning
# ---------------------------------------------------------------------


def clean_raw_text(
    raw_text: Optional[str],
) -> Optional[str]:
    """Perform basic whitespace cleanup on optional stored article text."""

    return clean_optional_text(raw_text)


def clean_news_record(
    ticker: str,
    article: Dict[str, Any],
    include_raw_text: bool = False,
) -> Dict[str, Any]:
    """
    Convert one stored article dictionary into the AI-layer record format.

    Database IDs are removed and ticker is added explicitly because news
    query dictionaries identify the company indirectly using company_id.
    """

    if not isinstance(article, dict):
        raise TypeError("article must be a dictionary.")

    clean_ticker = normalize_ticker(ticker)

    result = {
        "ticker": clean_ticker,
        "title": clean_optional_text(
            article.get("title")
        ),
        "source": clean_optional_text(
            article.get("source")
        ),
        "author": clean_optional_text(
            article.get("author")
        ),
        "published_at": coerce_optional_datetime(
            article.get("published_at")
        ),
        "url": normalize_url(
            article.get("url")
        ),
        "summary": clean_optional_text(
            article.get("summary")
        ),
        "sentiment_score": to_python_value(
            article.get("sentiment_score")
        ),
    }

    if include_raw_text:
        result["raw_text"] = clean_raw_text(
            article.get("raw_text")
        )

    return result


# ---------------------------------------------------------------------
# Refresh and persistence
# ---------------------------------------------------------------------


def refresh_company_news(
    ticker: str,
    days_back: int = DEFAULT_REFRESH_NEWS_DAYS_BACK,
    max_articles: int = DEFAULT_REFRESH_MAX_ARTICLES,
) -> Dict[str, Any]:
    """
    Fetch and store recent Finnhub company news.

    rows_fetched measures records returned by Finnhub. new_rows_added measures
    the actual database-count increase after URL-based deduplication.
    """

    clean_ticker = normalize_ticker(ticker)

    if days_back < 1:
        raise ValueError("days_back must be at least 1.")

    if max_articles < 1:
        raise ValueError("max_articles must be at least 1.")

    ensure_company_metadata(clean_ticker)

    stored_before = query.get_news_articles(
        clean_ticker,
        include_raw_text=False,
    )

    urls_before = {
        normalize_url(article.get("url"))
        for article in stored_before
        if normalize_url(article.get("url")) is not None
    }

    articles_df = fetch_news_articles(
        ticker=clean_ticker,
        days_back=days_back,
        max_articles=max_articles,
    )

    if articles_df is None:
        articles_df = pd.DataFrame()

    store_news_articles(
        clean_ticker,
        articles_df,
    )

    stored_after = query.get_news_articles(
        clean_ticker,
        include_raw_text=False,
    )

    newly_stored_articles = [
        article
        for article in stored_after
        if (
            normalize_url(article.get("url")) is not None
            and normalize_url(article.get("url"))
            not in urls_before
        )
    ]

    new_articles_by_source: Dict[str, int] = {}

    for article in newly_stored_articles:
        source = (
            clean_optional_text(article.get("source"))
            or "Unknown"
        )

        new_articles_by_source[source] = (
            new_articles_by_source.get(source, 0) + 1
        )

    return {
        "ticker": clean_ticker,
        "rows_fetched": int(len(articles_df)),
        "stored_count_before": int(len(stored_before)),
        "stored_count_after": int(len(stored_after)),
        "new_rows_added": int(len(newly_stored_articles)),
        "new_articles_by_source": new_articles_by_source,
        "days_back": days_back,
        "max_articles": max_articles,
    }


# ---------------------------------------------------------------------
# Point-in-time database retrieval
# ---------------------------------------------------------------------


def get_company_news(
    ticker: str,
    as_of_date: date,
    days_back: int = DEFAULT_RESEARCH_NEWS_DAYS_BACK,
    limit: Optional[int] = None,
    include_raw_text: bool = False,
) -> List[Dict[str, Any]]:
    """
    Retrieve articles published within a point-in-time research window.

    Unlike query.get_recent_news_articles(), the cutoff is based on the
    supplied as_of_date rather than the current system time.
    """

    clean_ticker = normalize_ticker(ticker)

    if days_back < 1:
        raise ValueError("days_back must be at least 1.")

    if limit is not None and limit < 0:
        raise ValueError("limit cannot be negative.")

    end_datetime = get_as_of_datetime(as_of_date)
    start_datetime = end_datetime - timedelta(
        days=days_back,
    )

    stored_articles = query.get_news_articles(
        clean_ticker,
        include_raw_text=include_raw_text,
    )

    filtered_articles = []

    for article in stored_articles:
        try:
            clean_article = clean_news_record(
                ticker=clean_ticker,
                article=article,
                include_raw_text=include_raw_text,
            )
        except (TypeError, ValueError):
            continue

        published_at = clean_article.get(
            "published_at"
        )

        if published_at is None:
            continue

        if published_at < start_datetime:
            continue

        if published_at > end_datetime:
            continue

        filtered_articles.append(clean_article)

    filtered_articles.sort(
        key=lambda item: (
            item.get("published_at")
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True,
    )

    if limit is not None:
        filtered_articles = filtered_articles[:limit]

    return filtered_articles


def get_latest_company_news(
    ticker: str,
    as_of_date: date,
    days_back: int = DEFAULT_RESEARCH_NEWS_DAYS_BACK,
    include_raw_text: bool = False,
) -> Optional[Dict[str, Any]]:
    """Retrieve the latest qualifying article by a requested as-of date."""

    articles = get_company_news(
        ticker=ticker,
        as_of_date=as_of_date,
        days_back=days_back,
        limit=1,
        include_raw_text=include_raw_text,
    )

    if not articles:
        return None

    return articles[0]


def get_news_article_by_url(
    url: str,
    ticker: Optional[str] = None,
    include_raw_text: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve one stored article by URL.

    If ticker is omitted, the function resolves the company through the
    article's company_id using query.get_company_by_id().
    """

    clean_url = normalize_url(url)

    if clean_url is None:
        raise ValueError("url cannot be empty.")

    article = query.get_news_article_by_url(
        url=clean_url,
        include_raw_text=include_raw_text,
    )

    if article is None:
        return None

    resolved_ticker = None

    if ticker is not None:
        resolved_ticker = normalize_ticker(ticker)
    else:
        company_id = article.get("company_id")

        if company_id is not None:
            company = query.get_company_by_id(
                int(company_id)
            )

            if company is not None:
                resolved_ticker = normalize_ticker(
                    company["ticker"]
                )

    if resolved_ticker is None:
        result = {
            str(key): to_python_value(value)
            for key, value in article.items()
            if key not in NEWS_INTERNAL_COLUMNS
        }

        result["published_at"] = (
            coerce_optional_datetime(
                result.get("published_at")
            )
        )

        result["title"] = clean_optional_text(
            result.get("title")
        )
        result["source"] = clean_optional_text(
            result.get("source")
        )
        result["author"] = clean_optional_text(
            result.get("author")
        )
        result["url"] = normalize_url(
            result.get("url")
        )
        result["summary"] = clean_optional_text(
            result.get("summary")
        )

        if include_raw_text:
            result["raw_text"] = clean_raw_text(
                result.get("raw_text")
            )

        return result

    return clean_news_record(
        ticker=resolved_ticker,
        article=article,
        include_raw_text=include_raw_text,
    )


# ---------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------


def normalize_search_text(value: Optional[str]) -> str:
    """Normalize text for deterministic matching."""

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value.lower(),
    ).strip()


def contains_term(
    text: str,
    term: str,
) -> bool:
    """Check for a normalized phrase within normalized text."""

    clean_text = normalize_search_text(text)
    clean_term = normalize_search_text(term)

    if not clean_term:
        return False

    return clean_term in clean_text


def ticker_appears_in_text(
    ticker: str,
    text: Optional[str],
) -> bool:
    """Detect a ticker as a standalone token or cashtag."""

    if text is None:
        return False

    clean_ticker = normalize_ticker(ticker)

    pattern = re.compile(
        rf"(?<![A-Za-z0-9])\$?{re.escape(clean_ticker)}"
        rf"(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )

    return pattern.search(text) is not None


def calculate_news_relevance_score(
    ticker: str,
    article: Dict[str, Any],
    company_name: Optional[str] = None,
    as_of_date: Optional[date] = None,
) -> float:
    """
    Estimate article relevance using deterministic title/summary rules.

    This score measures likely usefulness for company research. It is not a
    sentiment score and should not be interpreted as an expected-return signal.
    """

    clean_ticker = normalize_ticker(ticker)

    published_at = coerce_optional_datetime(
        article.get("published_at")
    )

    if (
        as_of_date is not None
        and published_at is not None
        and published_at > get_as_of_datetime(as_of_date)
    ):
        return -1.0

    title = clean_optional_text(
        article.get("title")
    ) or ""

    summary = clean_optional_text(
        article.get("summary")
    ) or ""

    title_text = normalize_search_text(title)
    summary_text = normalize_search_text(summary)

    clean_company_name = clean_optional_text(
        company_name
    )

    score = 0.0

    # Direct company references are the strongest relevance signals.
    if ticker_appears_in_text(clean_ticker, title):
        score += 5.0

    if ticker_appears_in_text(clean_ticker, summary):
        score += 2.5

    if clean_company_name:
        normalized_company_name = normalize_search_text(
            clean_company_name
        )

        if (
            normalized_company_name
            and normalized_company_name in title_text
        ):
            score += 5.0

        if (
            normalized_company_name
            and normalized_company_name in summary_text
        ):
            score += 2.5

        # The first meaningful word often captures the recognizable company
        # name when the formal name contains suffixes such as Corporation.
        company_tokens = re.findall(
            r"[a-z0-9]+",
            normalized_company_name,
        )

        if company_tokens:
            short_company_name = company_tokens[0]

            if (
                len(short_company_name) >= 4
                and re.search(
                    rf"\b{re.escape(short_company_name)}\b",
                    title_text,
                )
            ):
                score += 2.0

            if (
                len(short_company_name) >= 4
                and re.search(
                    rf"\b{re.escape(short_company_name)}\b",
                    summary_text,
                )
            ):
                score += 1.0

    title_material_matches = sum(
        1
        for keyword in NEWS_MATERIAL_KEYWORDS
        if contains_term(title_text, keyword)
    )

    summary_material_matches = sum(
        1
        for keyword in NEWS_MATERIAL_KEYWORDS
        if contains_term(summary_text, keyword)
    )

    score += min(
        title_material_matches * 1.25,
        4.0,
    )

    score += min(
        summary_material_matches * 0.50,
        3.0,
    )

    low_relevance_matches = sum(
        1
        for phrase in NEWS_LOW_RELEVANCE_PHRASES
        if (
            contains_term(title_text, phrase)
            or contains_term(summary_text, phrase)
        )
    )

    score -= min(
        low_relevance_matches * 1.75,
        5.0,
    )

    # Articles with neither a direct company reference nor a material topic
    # are often incidental ticker-association noise from the data provider.
    has_direct_reference = (
        ticker_appears_in_text(clean_ticker, title)
        or ticker_appears_in_text(clean_ticker, summary)
        or (
            clean_company_name is not None
            and (
                normalize_search_text(clean_company_name)
                in title_text
                or normalize_search_text(clean_company_name)
                in summary_text
            )
        )
    )

    if (
        not has_direct_reference
        and title_material_matches == 0
        and summary_material_matches == 0
    ):
        score -= 3.0

    if not summary:
        score -= 0.75

    if not title:
        score -= 2.0

    # Small recency bonus. It helps order similarly relevant articles but
    # cannot overpower direct company relevance.
    published_at = coerce_optional_datetime(
        article.get("published_at")
    )

    if (
        as_of_date is not None
        and published_at is not None
    ):
        as_of_datetime = get_as_of_datetime(
            as_of_date
        )

        age_days = max(
            (as_of_datetime - published_at).days,
            0,
        )

        if age_days <= 7:
            score += 1.25
        elif age_days <= 30:
            score += 0.75
        elif age_days <= 90:
            score += 0.25

    #if published_at - as_of_datetime > timedelta(days=0):
     #   score -= 1.0

    return float(round(score, 6))


def rank_news_articles(
    ticker: str,
    articles: Sequence[Dict[str, Any]],
    company_name: Optional[str] = None,
    as_of_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Attach relevance scores and sort articles from strongest to weakest."""

    ranked_articles = []

    as_of_datetime = (
        get_as_of_datetime(as_of_date)
        if as_of_date is not None
        else None
    )

    for article in articles:

        published_at = coerce_optional_datetime(
            article.get("published_at")
        )

        if (
            as_of_datetime is not None
            and published_at is not None
            and published_at > as_of_datetime
        ):
            continue

        clean_article = dict(article)
        clean_article["published_at"] = published_at

        clean_article["relevance_score"] = (
            calculate_news_relevance_score(
                ticker=ticker,
                article=clean_article,
                company_name=company_name,
                as_of_date=as_of_date,
            )
        )

        ranked_articles.append(clean_article)

    ranked_articles.sort(
        key=lambda item: (
            float(item.get("relevance_score") or 0.0),
            item.get("published_at")
            or datetime.min.replace(
                tzinfo=timezone.utc
            ),
        ),
        reverse=True,
    )

    return ranked_articles


# ---------------------------------------------------------------------
# Duplicate-event reduction
# ---------------------------------------------------------------------


def tokenize_title(
    title: Optional[str],
) -> Set[str]:
    """Convert one title into meaningful lowercase comparison tokens."""

    clean_title = normalize_search_text(title)

    if not clean_title:
        return set()

    tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            clean_title,
        )
        if (
            len(token) >= 2
            and token not in TITLE_STOPWORDS
        )
    }

    return tokens


def calculate_jaccard_similarity(
    left_tokens: Set[str],
    right_tokens: Set[str],
) -> float:
    """Calculate Jaccard similarity between two token sets."""

    if not left_tokens or not right_tokens:
        return 0.0

    intersection_size = len(
        left_tokens & right_tokens
    )
    union_size = len(
        left_tokens | right_tokens
    )

    if union_size == 0:
        return 0.0

    return intersection_size / union_size


def deduplicate_similar_news_articles(
    articles: Sequence[Dict[str, Any]],
    similarity_threshold: float = (
        DEFAULT_DUPLICATE_TITLE_SIMILARITY
    ),
) -> List[Dict[str, Any]]:
    """
    Remove likely duplicate coverage using URL and title-token similarity.

    Input should normally be relevance-ranked first. The first article in a
    duplicate group is retained, which means the strongest-ranked article is
    preserved.
    """

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError(
            "similarity_threshold must be between 0 and 1."
        )

    selected = []
    selected_urls = set()
    selected_token_sets = []

    for article in articles:
        article_url = normalize_url(
            article.get("url")
        )

        if (
            article_url is not None
            and article_url in selected_urls
        ):
            continue

        article_tokens = tokenize_title(
            article.get("title")
        )

        is_similar = False

        for existing_tokens in selected_token_sets:
            similarity = calculate_jaccard_similarity(
                article_tokens,
                existing_tokens,
            )

            if similarity >= similarity_threshold:
                is_similar = True
                break

        if is_similar:
            continue

        selected.append(dict(article))
        selected_token_sets.append(article_tokens)

        if article_url is not None:
            selected_urls.add(article_url)

    return selected


def select_relevant_news_articles(
    ticker: str,
    articles: Sequence[Dict[str, Any]],
    company_name: Optional[str],
    as_of_date: date,
    limit: int,
    minimum_relevance_score: float = (
        DEFAULT_MINIMUM_RELEVANCE_SCORE
    ),
    duplicate_similarity_threshold: float = (
        DEFAULT_DUPLICATE_TITLE_SIMILARITY
    ),
) -> List[Dict[str, Any]]:
    """
    Rank, deduplicate, and select the strongest articles.

    Articles meeting the relevance threshold are preferred. If fewer than the
    requested limit pass the threshold, the best remaining articles fill the
    unused positions so sparse-news companies still receive some context.
    """

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    ranked = rank_news_articles(
        ticker=ticker,
        articles=articles,
        company_name=company_name,
        as_of_date=as_of_date,
    )

    deduplicated = deduplicate_similar_news_articles(
        articles=ranked,
        similarity_threshold=(
            duplicate_similarity_threshold
        ),
    )

    qualifying = [
        article
        for article in deduplicated
        if float(
            article.get("relevance_score") or 0.0
        ) >= minimum_relevance_score
    ]

    selected = qualifying[:limit]

    if len(selected) < limit:
        selected_identifiers = {
            (
                normalize_url(article.get("url")),
                clean_optional_text(article.get("title")),
            )
            for article in selected
        }

        for article in deduplicated:
            identifier = (
                normalize_url(article.get("url")),
                clean_optional_text(article.get("title")),
            )

            if identifier in selected_identifiers:
                continue

            selected.append(article)
            selected_identifiers.add(identifier)

            if len(selected) >= limit:
                break

    return selected


# ---------------------------------------------------------------------
# Optional raw-text excerpt support
# ---------------------------------------------------------------------


def build_raw_text_excerpt(
    raw_text: Optional[str],
    max_characters: int = (
        DEFAULT_RAW_TEXT_EXCERPT_CHARACTERS
    ),
) -> Optional[str]:
    """
    Build a bounded excerpt when full article text is already stored.

    The function does not fetch a publisher page. For current Finnhub records,
    raw_text is usually None and this function therefore returns None.
    """

    if max_characters < 1:
        raise ValueError(
            "max_characters must be at least 1."
        )

    clean_text = clean_raw_text(raw_text)

    if clean_text is None:
        return None

    if len(clean_text) <= max_characters:
        return clean_text

    truncated = clean_text[:max_characters]

    last_period = truncated.rfind(".")
    last_space = truncated.rfind(" ")

    if last_period >= int(max_characters * 0.75):
        truncated = truncated[:last_period + 1]
    elif last_space >= int(max_characters * 0.85):
        truncated = truncated[:last_space]

    return truncated.rstrip() + " ..."


# ---------------------------------------------------------------------
# NewsEvidence construction
# ---------------------------------------------------------------------


def build_news_evidence(
    ticker: str,
    article: Dict[str, Any],
    include_raw_text_excerpt: bool = True,
    raw_text_excerpt_characters: int = (
        DEFAULT_RAW_TEXT_EXCERPT_CHARACTERS
    ),
) -> NewsEvidence:
    """
    Convert one cleaned article into validated NewsEvidence.

    Current Finnhub records generally produce raw_text_excerpt=None. The title,
    short summary, source, timestamp, and URL remain available to the agent,
    which must not claim to have read the publisher's full article.
    """

    clean_ticker = normalize_ticker(ticker)

    title = clean_optional_text(
        article.get("title")
    )

    if title is None:
        raise ValueError(
            "News article must contain a non-empty title."
        )

    related_tickers_value = article.get(
        "related_tickers"
    )

    if isinstance(
        related_tickers_value,
        (list, tuple, set),
    ):
        related_tickers = normalize_ticker_list(
            related_tickers_value
        )
    else:
        related_tickers = [clean_ticker]

    if clean_ticker not in related_tickers:
        related_tickers.insert(0, clean_ticker)

    raw_text_excerpt = None

    if include_raw_text_excerpt:
        raw_text_excerpt = build_raw_text_excerpt(
            raw_text=article.get("raw_text"),
            max_characters=(
                raw_text_excerpt_characters
            ),
        )

    return NewsEvidence(
        ticker=clean_ticker,
        related_tickers=related_tickers,
        title=title,
        source=clean_optional_text(
            article.get("source")
        ),
        published_at=coerce_optional_datetime(
            article.get("published_at")
        ),
        url=normalize_url(
            article.get("url")
        ),
        summary=clean_optional_text(
            article.get("summary")
        ),
        raw_text_excerpt=raw_text_excerpt,
    )


def get_news_evidence(
    ticker: str,
    as_of_date: date,
    days_back: int = DEFAULT_RESEARCH_NEWS_DAYS_BACK,
    limit: int = DEFAULT_RESEARCH_NEWS_LIMIT,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = False,
    include_raw_text_excerpt: bool = True,
    minimum_relevance_score: float = (
        DEFAULT_MINIMUM_RELEVANCE_SCORE
    ),
) -> List[NewsEvidence]:
    """
    Retrieve, rank, deduplicate, and validate news evidence for one company.

    refresh_if_missing fetches news only when no qualifying records are stored
    in the requested window.

    refresh_recent_data performs a current Finnhub refresh even when stored
    articles already exist. This should normally remain False for historical
    point-in-time research.

    For the first version, the evidence normally contains Finnhub summaries
    rather than full article bodies.
    """

    clean_ticker = normalize_ticker(ticker)

    if days_back < 1:
        raise ValueError("days_back must be at least 1.")

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    existing_articles = get_company_news(
        ticker=clean_ticker,
        as_of_date=as_of_date,
        days_back=days_back,
        limit=None,
        include_raw_text=include_raw_text_excerpt,
    )

    if refresh_recent_data:
        refresh_company_news(
            ticker=clean_ticker,
            days_back=max(
                days_back,
                DEFAULT_REFRESH_NEWS_DAYS_BACK,
            ),
            max_articles=(
                DEFAULT_REFRESH_MAX_ARTICLES
            ),
        )

        existing_articles = get_company_news(
            ticker=clean_ticker,
            as_of_date=as_of_date,
            days_back=days_back,
            limit=None,
            include_raw_text=(
                include_raw_text_excerpt
            ),
        )

    elif refresh_if_missing and not existing_articles:
        refresh_company_news(
            ticker=clean_ticker,
            days_back=max(
                days_back,
                DEFAULT_REFRESH_NEWS_DAYS_BACK,
            ),
            max_articles=(
                DEFAULT_REFRESH_MAX_ARTICLES
            ),
        )

        existing_articles = get_company_news(
            ticker=clean_ticker,
            as_of_date=as_of_date,
            days_back=days_back,
            limit=None,
            include_raw_text=(
                include_raw_text_excerpt
            ),
        )

    company = query.get_company_by_ticker(
        clean_ticker
    )

    company_name = None

    if company is not None:
        company_name = (
            clean_optional_text(company.get("name"))
            or clean_optional_text(
                company.get("company_name")
            )
        )

    selected_articles = select_relevant_news_articles(
        ticker=clean_ticker,
        articles=existing_articles,
        company_name=company_name,
        as_of_date=as_of_date,
        limit=limit,
        minimum_relevance_score=(
            minimum_relevance_score
        ),
    )

    evidence = []

    for article in selected_articles:
        try:
            evidence.append(
                build_news_evidence(
                    ticker=clean_ticker,
                    article=article,
                    include_raw_text_excerpt=(
                        include_raw_text_excerpt
                    ),
                )
            )
        except (TypeError, ValueError):
            continue

    return evidence


def get_holding_news_evidence(
    ticker: str,
    as_of_date: date,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = False,
    include_raw_text_excerpt: bool = True,
) -> List[NewsEvidence]:
    """Retrieve the smaller default news set for one portfolio holding."""

    return get_news_evidence(
        ticker=ticker,
        as_of_date=as_of_date,
        days_back=DEFAULT_HOLDING_NEWS_DAYS_BACK,
        limit=DEFAULT_HOLDING_NEWS_LIMIT,
        refresh_if_missing=refresh_if_missing,
        refresh_recent_data=refresh_recent_data,
        include_raw_text_excerpt=(
            include_raw_text_excerpt
        ),
    )


def get_news_evidence_for_tickers(
    tickers: Iterable[str],
    as_of_date: date,
    days_back: int = DEFAULT_RESEARCH_NEWS_DAYS_BACK,
    limit_per_ticker: int = DEFAULT_RESEARCH_NEWS_LIMIT,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = False,
    include_raw_text_excerpt: bool = True,
    minimum_relevance_score: float = (
        DEFAULT_MINIMUM_RELEVANCE_SCORE
    ),
) -> Dict[str, List[NewsEvidence]]:
    """
    Retrieve news evidence for multiple companies.

    Errors are isolated by ticker so one Finnhub or database failure does not
    prevent research for the remaining companies.
    """

    clean_tickers = normalize_ticker_list(
        tickers
    )

    results: Dict[str, List[NewsEvidence]] = {}

    for ticker in clean_tickers:
        try:
            results[ticker] = get_news_evidence(
                ticker=ticker,
                as_of_date=as_of_date,
                days_back=days_back,
                limit=limit_per_ticker,
                refresh_if_missing=(
                    refresh_if_missing
                ),
                refresh_recent_data=(
                    refresh_recent_data
                ),
                include_raw_text_excerpt=(
                    include_raw_text_excerpt
                ),
                minimum_relevance_score=(
                    minimum_relevance_score
                ),
            )
        except Exception:
            results[ticker] = []

    return results


def get_holding_news_evidence_for_tickers(
    tickers: Iterable[str],
    as_of_date: date,
    refresh_if_missing: bool = True,
    refresh_recent_data: bool = False,
    include_raw_text_excerpt: bool = True,
) -> Dict[str, List[NewsEvidence]]:
    """Retrieve compact holding-news evidence for multiple tickers."""

    return get_news_evidence_for_tickers(
        tickers=tickers,
        as_of_date=as_of_date,
        days_back=DEFAULT_HOLDING_NEWS_DAYS_BACK,
        limit_per_ticker=DEFAULT_HOLDING_NEWS_LIMIT,
        refresh_if_missing=refresh_if_missing,
        refresh_recent_data=refresh_recent_data,
        include_raw_text_excerpt=(
            include_raw_text_excerpt
        ),
    )


__all__ = [
    "DEFAULT_RESEARCH_NEWS_DAYS_BACK",
    "DEFAULT_RESEARCH_NEWS_LIMIT",
    "DEFAULT_HOLDING_NEWS_DAYS_BACK",
    "DEFAULT_HOLDING_NEWS_LIMIT",
    "DEFAULT_REFRESH_NEWS_DAYS_BACK",
    "DEFAULT_REFRESH_MAX_ARTICLES",
    "DEFAULT_RAW_TEXT_EXCERPT_CHARACTERS",
    "DEFAULT_MINIMUM_RELEVANCE_SCORE",
    "DEFAULT_DUPLICATE_TITLE_SIMILARITY",
    "NEWS_MATERIAL_KEYWORDS",
    "NEWS_LOW_RELEVANCE_PHRASES",
    "normalize_ticker",
    "normalize_ticker_list",
    "clean_news_record",
    "refresh_company_news",
    "get_company_news",
    "get_latest_company_news",
    "get_news_article_by_url",
    "calculate_news_relevance_score",
    "rank_news_articles",
    "calculate_jaccard_similarity",
    "deduplicate_similar_news_articles",
    "select_relevant_news_articles",
    "build_raw_text_excerpt",
    "build_news_evidence",
    "get_news_evidence",
    "get_holding_news_evidence",
    "get_news_evidence_for_tickers",
    "get_holding_news_evidence_for_tickers",
]