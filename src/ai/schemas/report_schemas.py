# src/ai/schemas/report_schemas.py

"""
Structured LLM-output schemas for investment research reports.

These models constrain agent output so reports can be validated, displayed
in Streamlit, serialized through APIs, and persisted later if needed.
"""

from datetime import date
from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


EvidenceSourceType = Literal[
    "quantitative",
    "company_data",
    "news",
    "sec_filing",
]

ResearchConfidence = Literal[
    "low",
    "moderate",
    "high",
]


def normalize_ticker(value: str, field_name: str = "ticker") -> str:
    """Normalize and validate one report ticker."""

    clean_value = str(value).upper().strip()

    if not clean_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return clean_value


def normalize_ticker_list(values: List[str]) -> List[str]:
    """Normalize and deduplicate report ticker lists."""

    normalized = []
    seen = set()

    for ticker in values:
        clean_ticker = normalize_ticker(ticker)

        if clean_ticker in seen:
            continue

        seen.add(clean_ticker)
        normalized.append(clean_ticker)

    return normalized


class StrictReportSchema(BaseModel):
    """
    Shared validation behavior for LLM-generated report objects.

    Extra fields are forbidden so malformed or hallucinated output keys are
    rejected instead of silently entering the final report.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class EvidenceReference(StrictReportSchema):
    """
    Identifies evidence supporting a specific report claim.

    The dashboard or future PDF renderer can display these references beside
    important conclusions.
    """

    ticker: Optional[str] = None

    source_type: EvidenceSourceType

    title: str = Field(
        min_length=1,
        description="Human-readable name of the supporting source.",
    )

    claim_supported: str = Field(
        min_length=1,
        description="The specific report claim supported by this evidence.",
    )

    source_date: Optional[date] = None
    url: Optional[str] = None


class HoldingReport(StrictReportSchema):
    """
    LLM-generated analysis for one selected portfolio holding.

    The quantitative engine remains authoritative for the ticker and weight.
    The agent explains the allocation but must not independently change it.
    """

    ticker: str

    company_name: str = Field(
        min_length=1,
        description="Official company name.",
    )

    portfolio_weight: float = Field(
        ge=0.0,
        le=1.0,
    )

    summary: str = Field(
        min_length=1,
        description=(
            "Concise overview of the holding and its role in the portfolio."
        ),
    )

    investment_thesis: str = Field(
        min_length=1,
        description=(
            "Evidence-based explanation of why the company may be "
            "attractive."
        ),
    )

    selection_rationale: str = Field(
        min_length=1,
        description=(
            "Explanation of the factor scores, expected-return signal, and "
            "other deterministic evidence associated with the selection."
        ),
    )

    quantitative_strengths: List[str] = Field(default_factory=list)
    quantitative_weaknesses: List[str] = Field(default_factory=list)

    catalysts: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recent_developments: List[str] = Field(default_factory=list)
    monitoring_items: List[str] = Field(default_factory=list)

    evidence: List[EvidenceReference] = Field(default_factory=list)

    confidence: ResearchConfidence = "moderate"

    confidence_explanation: str = Field(
        min_length=1,
        description=(
            "Explanation of why the available evidence supports the "
            "assigned confidence level."
        ),
    )

    @field_validator("ticker")
    @classmethod
    def normalize_holding_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class PortfolioRiskReport(StrictReportSchema):
    """
    Structured portfolio-level risk assessment.

    This captures risks that may not be obvious when reviewing each holding
    independently.
    """

    concentration_risks: List[str] = Field(default_factory=list)
    sector_risks: List[str] = Field(default_factory=list)
    factor_exposures: List[str] = Field(default_factory=list)
    correlation_risks: List[str] = Field(default_factory=list)
    event_risks: List[str] = Field(default_factory=list)
    liquidity_or_data_warnings: List[str] = Field(default_factory=list)

    overall_risk_summary: str = Field(
        min_length=1,
        description="Overall interpretation of portfolio-level risk.",
    )


class QuarterlyPortfolioReport(StrictReportSchema):
    """
    Main structured output produced by the quarterly portfolio agent.

    The schema is suitable for dashboard display, API serialization, report
    persistence, and later conversion into a PDF or other research document.
    """

    as_of_date: date

    portfolio_method: str = Field(
        min_length=1,
    )

    executive_summary: str = Field(
        min_length=1,
        description="High-level explanation of the current portfolio.",
    )

    selected_tickers: List[str] = Field(
        min_length=1,
    )

    holdings: List[HoldingReport] = Field(
        min_length=1,
    )

    allocation_summary: str = Field(
        min_length=1,
        description=(
            "Explanation of portfolio concentration and relative "
            "allocations."
        ),
    )

    portfolio_risk_analysis: PortfolioRiskReport

    key_portfolio_catalysts: List[str] = Field(default_factory=list)
    monitoring_priorities: List[str] = Field(default_factory=list)

    methodology_notes: List[str] = Field(
        default_factory=list,
        description=(
            "Brief explanation of factor selection, statistical expected "
            "returns, and portfolio construction."
        ),
    )

    limitations: List[str] = Field(
        default_factory=list,
        description=(
            "Important limitations of the data, models, and research "
            "process."
        ),
    )

    @field_validator("selected_tickers")
    @classmethod
    def normalize_selected_tickers(
        cls,
        values: List[str],
    ) -> List[str]:
        normalized = normalize_ticker_list(values)

        if not normalized:
            raise ValueError(
                "At least one selected ticker must be provided."
            )

        return normalized

    @model_validator(mode="after")
    def validate_portfolio_report(self) -> "QuarterlyPortfolioReport":
        holding_tickers = [holding.ticker for holding in self.holdings]

        if len(holding_tickers) != len(set(holding_tickers)):
            raise ValueError(
                "Each holding ticker must appear only once."
            )

        selected_set = set(self.selected_tickers)
        holding_set = set(holding_tickers)

        missing_holding_reports = selected_set - holding_set

        if missing_holding_reports:
            raise ValueError(
                "Every selected ticker must have a corresponding "
                "HoldingReport."
            )

        unexpected_holding_reports = holding_set - selected_set

        if unexpected_holding_reports:
            raise ValueError(
                "Every HoldingReport ticker must appear in selected_tickers."
            )

        total_weight = sum(
            holding.portfolio_weight
            for holding in self.holdings
        )

        if total_weight > 1.000001:
            raise ValueError(
                "Holding portfolio weights cannot sum to more than 1."
            )

        return self


class CompanyResearchReport(StrictReportSchema):
    """
    Main structured output produced by the single-company research agent.

    It combines quantitative evidence, financial history, SEC filings, and
    news into one consistent company-level report.
    """

    as_of_date: date
    ticker: str

    company_name: str = Field(
        min_length=1,
        description="Official company name.",
    )

    company_overview: str = Field(min_length=1)
    investment_thesis: str = Field(min_length=1)
    quantitative_assessment: str = Field(min_length=1)

    factor_strengths: List[str] = Field(default_factory=list)
    factor_weaknesses: List[str] = Field(default_factory=list)
    financial_trends: List[str] = Field(default_factory=list)

    valuation_observations: List[str] = Field(default_factory=list)
    recent_developments: List[str] = Field(default_factory=list)

    catalysts: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    monitoring_items: List[str] = Field(default_factory=list)

    evidence: List[EvidenceReference] = Field(default_factory=list)

    confidence: ResearchConfidence = "moderate"

    confidence_explanation: str = Field(
        min_length=1,
        description=(
            "Explanation of why the available evidence supports the "
            "assigned confidence level."
        ),
    )

    limitations: List[str] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def normalize_company_report_ticker(cls, value: str) -> str:
        return normalize_ticker(value)