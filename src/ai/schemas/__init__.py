# src/ai/schemas/__init__.py

"""
Public schema interface for the AI research layer.

The package exposes:
- validated request schemas;
- deterministic research-context schemas;
- structured LLM report-output schemas.

Internal normalization helpers remain inside their defining modules.
"""

from src.ai.schemas.research_schemas import (
    CompanyResearchContext,
    CompanyResearchRequest,
    FilingEvidence,
    HoldingResearchContext,
    NewsEvidence,
    PortfolioResearchContext,
    QuarterlyResearchRequest,
)

from src.ai.schemas.report_schemas import (
    CompanyResearchReport,
    EvidenceReference,
    HoldingReport,
    PortfolioRiskReport,
    QuarterlyPortfolioReport,
)


__all__ = [
    # Research requests
    "QuarterlyResearchRequest",
    "CompanyResearchRequest",

    # Evidence and deterministic context
    "NewsEvidence",
    "FilingEvidence",
    "HoldingResearchContext",
    "PortfolioResearchContext",
    "CompanyResearchContext",

    # Structured LLM report output
    "EvidenceReference",
    "HoldingReport",
    "PortfolioRiskReport",
    "QuarterlyPortfolioReport",
    "CompanyResearchReport",
]