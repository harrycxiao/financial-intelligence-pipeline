# src/ai/schemas/research_schemas.py

"""
Validated input and research-context schemas for the AI layer.

These models represent deterministic data assembled by tools and services
before that data is supplied to an LLM agent.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from pathlib import Path
import pandas as pd

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


PortfolioMethod = Literal[
    "equal_weight",
    "top_n_equal_weight",
    "score_weighted",
    "risk_adjusted_score_weighted",
    "minimum_variance",
    "maximum_sharpe",
    "mean_variance",
    "risk_parity",
    "hierarchical_risk_parity",
]

PeriodMode = Literal[
    "quarterly",
    "annual",
    "raw",
]


def fetch_us_universe_tickers(
    limit: Optional[int] = None,
    eligible_csv_path: str = "results/us_universe_eligible_tickers.csv",
) -> list[str]:
    path = Path(eligible_csv_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Could not find eligible ticker file: {eligible_csv_path}. "
            "Run scripts/filter_us_universe.py first."
        )

    df = pd.read_csv(path)

    if "ticker" not in df.columns:
        raise ValueError(f"{eligible_csv_path} must contain a 'ticker' column.")

    tickers = (
        df["ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
        .drop_duplicates()
        .tolist()
    )

    if limit is not None:
        return tickers[:limit]

    return tickers


def normalize_ticker(value: str, field_name: str = "ticker") -> str:
    """Normalize and validate one ticker symbol."""

    clean_value = str(value).upper().strip()

    if not clean_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return clean_value


def normalize_ticker_list(values: List[str]) -> List[str]:
    """Normalize, deduplicate, and validate a ticker list."""

    normalized = []
    seen = set()

    for ticker in values:
        clean_ticker = normalize_ticker(ticker)

        if clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        normalized.append(clean_ticker)

    return normalized


class StrictSchema(BaseModel):
    """
    Shared base class for deterministic AI-layer schemas.

    Unknown fields are rejected so naming mistakes are caught before invalid
    information enters an agent's context.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class NewsEvidence(StrictSchema):
    """
    Compact representation of one news article supplied to an agent.

    Full article bodies should normally be reduced to a summary or excerpt
    before constructing this schema.
    """
    ticker: str
    related_tickers: List[str] = Field(default_factory=list)
    title: str = Field(min_length=1)
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    url: Optional[str] = None

    summary: Optional[str] = None
    raw_text_excerpt: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def normalize_holding_ticker(cls, value: str) -> str:
        return normalize_ticker(value)

    @field_validator("related_tickers")
    @classmethod
    def normalize_related_tickers(cls, values: List[str]) -> List[str]:
        return normalize_ticker_list(values)

class FilingEvidence(StrictSchema):
    """
    Compact representation of one SEC filing supplied to an agent.

    relevant_excerpt should contain only the filing section needed for the
    current research task rather than the complete filing text.
    """

    ticker: str
    filing_type: str = Field(min_length=1)
    filing_date: Optional[date] = None
    accession_number: Optional[str] = None
    filing_url: Optional[str] = None

    summary: Optional[str] = None
    relevant_excerpt: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def normalize_holding_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class HoldingResearchContext(StrictSchema):
    """
    Verified quantitative and textual context for one selected holding.

    research_service.py constructs this object and supplies it to the
    quarterly portfolio agent.
    """

    ticker: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    portfolio_weight: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Portfolio allocation produced by the deterministic "
            "quantitative engine."
        ),
    )

    universe_rank: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Factor-score rank among the complete eligible stock universe."
        ),
    )

    screen_rank: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Factor-score rank after rescoring stocks within the top screen."
        ),
    )

    overall_score: Optional[float] = None
    expected_excess_return: Optional[float] = None

    factor_scores: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description=(
            "Named factor-category scores, such as value_score and "
            "quality_score."
        ),
    )

    derived_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Underlying derived financial, market, risk, and technical "
            "metrics used by the factor system."
        ),
    )

    recent_news: List[NewsEvidence] = Field(default_factory=list)
    recent_filings: List[FilingEvidence] = Field(default_factory=list)

    data_warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Missing, stale, incomplete, or otherwise limited evidence "
            "associated with this holding."
        ),
    )

    @field_validator("ticker")
    @classmethod
    def normalize_holding_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class PortfolioResearchContext(StrictSchema):
    """
    Complete deterministic context supplied to the portfolio-report agent.

    This contains selected holdings and supporting evidence but intentionally
    excludes full-universe dataframes that would unnecessarily consume LLM
    context.
    """

    as_of_date: date
    portfolio_method: PortfolioMethod
    period_mode: PeriodMode = "quarterly"

    benchmark_ticker: Optional[str] = "SPY"

    universe_size: int = Field(ge=0)
    eligible_universe_size: int = Field(ge=0)

    screened_tickers: List[str] = Field(default_factory=list)
    selected_tickers: List[str] = Field(default_factory=list)

    portfolio_weights: Dict[str, float] = Field(default_factory=dict)
    holdings: List[HoldingResearchContext] = Field(default_factory=list)

    configuration: Dict[str, Any] = Field(default_factory=dict)

    data_freshness_notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("benchmark_ticker")
    @classmethod
    def normalize_benchmark_ticker(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        return normalize_ticker(value, field_name="benchmark_ticker")

    @field_validator("screened_tickers", "selected_tickers")
    @classmethod
    def normalize_portfolio_ticker_lists(
        cls,
        values: List[str],
    ) -> List[str]:
        return normalize_ticker_list(values)

    @field_validator("portfolio_weights")
    @classmethod
    def validate_portfolio_weights(
        cls,
        value: Dict[str, float],
    ) -> Dict[str, float]:
        normalized = {}

        for ticker, weight in value.items():
            clean_ticker = normalize_ticker(
                ticker,
                field_name="portfolio weight ticker",
            )
            numeric_weight = float(weight)

            if numeric_weight < 0.0 or numeric_weight > 1.0:
                raise ValueError(
                    "Each long-only portfolio weight must be between 0 and 1."
                )

            normalized[clean_ticker] = numeric_weight

        total_weight = sum(normalized.values())

        if total_weight > 1.000001:
            raise ValueError("Portfolio weights cannot sum to more than 1.")

        return normalized

    @model_validator(mode="after")
    def validate_portfolio_context(self) -> "PortfolioResearchContext":
        selected_set = set(self.selected_tickers)
        holding_tickers = [holding.ticker for holding in self.holdings]

        if len(holding_tickers) != len(set(holding_tickers)):
            raise ValueError(
                "Each holding ticker must appear only once in holdings."
            )

        unknown_holdings = set(holding_tickers) - selected_set

        if unknown_holdings:
            raise ValueError(
                "Every holding ticker must also appear in selected_tickers."
            )

        unknown_weight_tickers = (
            set(self.portfolio_weights.keys()) - selected_set
        )

        if unknown_weight_tickers:
            raise ValueError(
                "Every portfolio-weight ticker must appear in "
                "selected_tickers."
            )

        return self


class CompanyResearchContext(StrictSchema):
    """
    Deterministic evidence supplied to the single-company research agent.

    Unlike HoldingResearchContext, this model can represent any company,
    whether or not it is currently included in the portfolio.
    """

    as_of_date: date

    ticker: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None

    is_current_holding: bool = False

    portfolio_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    universe_rank: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Factor-score rank among the complete eligible stock universe."
        ),
    )

    screen_rank: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Factor-score rank after rescoring stocks within the top screen."
        ),
    )

    overall_score: Optional[float] = None
    expected_excess_return: Optional[float] = None

    factor_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    derived_metrics: Dict[str, Any] = Field(default_factory=dict)

    financial_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Point-in-time raw or reconstructed financial-statement history."
        ),
    )

    fundamental_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Latest derived fundamental metrics together with longer-term "
            "annual growth summaries."
        ),
    )

    market_history_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Market-performance, risk, and latest technical-indicator summary."
        ),
    )

    recent_news: List[NewsEvidence] = Field(default_factory=list)
    recent_filings: List[FilingEvidence] = Field(default_factory=list)

    comparison_tickers: List[str] = Field(default_factory=list)
    data_warnings: List[str] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def normalize_company_ticker(cls, value: str) -> str:
        return normalize_ticker(value)

    @field_validator("comparison_tickers")
    @classmethod
    def normalize_company_comparison_tickers(
        cls,
        values: List[str],
    ) -> List[str]:
        return normalize_ticker_list(values)

    @model_validator(mode="after")
    def validate_holding_fields(self) -> "CompanyResearchContext":
        if not self.is_current_holding and self.portfolio_weight is not None:
            raise ValueError(
                "portfolio_weight should be omitted when "
                "is_current_holding is False."
            )

        return self


class QuarterlyResearchRequest(StrictSchema):
    """
    Typed input for the quarterly research service.

    The service uses this request to run the quantitative engine, retrieve
    selected-company evidence, and build PortfolioResearchContext.
    """

    as_of_date: date

    universe_tickers: List[str] = Field(
        default=fetch_us_universe_tickers(),
        min_length=1,
        description="Ticker universe supplied to the research engine.",
    )

    portfolio_method: PortfolioMethod = "score_weighted"
    period_mode: PeriodMode = "quarterly"

    top_screen_n: int = Field(
        default=100,
        ge=1,
    )

    final_portfolio_n: int = Field(
        default=5,
        ge=1,
    )

    include_news: bool = True

    news_days_back: int = Field(
        default=30,
        ge=1,
        le=365,
    )

    max_news_articles_per_ticker: int = Field(
        default=10,
        ge=0,
        le=100,
    )

    include_filings: bool = True

    filing_limit_per_ticker: int = Field(
        default=5,
        ge=0,
        le=25,
    )

    refresh_quantitative_inputs: bool = True
    refresh_recent_data: bool = False
    use_cache: bool = True

    @field_validator("universe_tickers")
    @classmethod
    def normalize_universe_tickers(
        cls,
        values: List[str],
    ) -> List[str]:
        normalized = normalize_ticker_list(values)

        if not normalized:
            raise ValueError(
                "At least one valid universe ticker is required."
            )

        return normalized

    @model_validator(mode="after")
    def validate_quarterly_request(self) -> "QuarterlyResearchRequest":
        if self.final_portfolio_n > self.top_screen_n:
            raise ValueError(
                "final_portfolio_n cannot be greater than top_screen_n."
            )

        if self.top_screen_n > len(self.universe_tickers):
            raise ValueError(
                "top_screen_n cannot be greater than the number of "
                "unique universe tickers."
            )

        if not self.include_news and self.max_news_articles_per_ticker != 10:
            raise ValueError(
                "max_news_articles_per_ticker should remain at its default "
                "when include_news is False."
            )

        if not self.include_filings and self.filing_limit_per_ticker != 5:
            raise ValueError(
                "filing_limit_per_ticker should remain at its default "
                "when include_filings is False."
            )

        return self


class CompanyResearchRequest(StrictSchema):
    """
    Typed input for the single-company research service.

    It controls which evidence the service retrieves before constructing
    CompanyResearchContext.
    """

    ticker: str
    as_of_date: date

    include_financial_history: bool = True

    financial_history_limit: int = Field(
        default=12,
        ge=1,
        le=40,
    )

    include_news: bool = True

    news_days_back: int = Field(
        default=90,
        ge=1,
        le=730,
    )

    max_news_articles: int = Field(
        default=15,
        ge=0,
        le=100,
    )

    include_filings: bool = True

    filing_limit: int = Field(
        default=5,
        ge=0,
        le=25,
    )

    comparison_tickers: List[str] = Field(default_factory=list)
    refresh_recent_data: bool = False

    @field_validator("ticker")
    @classmethod
    def normalize_request_ticker(cls, value: str) -> str:
        return normalize_ticker(value)

    @field_validator("comparison_tickers")
    @classmethod
    def normalize_request_comparison_tickers(
        cls,
        values: List[str],
    ) -> List[str]:
        return normalize_ticker_list(values)

    @model_validator(mode="after")
    def validate_company_request(self) -> "CompanyResearchRequest":
        if self.ticker in self.comparison_tickers:
            self.comparison_tickers = [
                ticker
                for ticker in self.comparison_tickers
                if ticker != self.ticker
            ]

        return self