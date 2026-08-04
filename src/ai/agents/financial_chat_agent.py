"""
General-purpose financial chatbot agent.

This module:
- configures the PydanticAI financial chat agent;
- registers simple chat-facing tools;
- delegates all financial retrieval and processing to deterministic tools;
- returns natural-language answers as strings.

This module does not contain database, ingestion, financial-calculation,
news-ranking, or filing-extraction logic.
"""

from datetime import date
from typing import Any, Dict, List

from pydantic_ai import Agent

from src.ai.prompts.financial_chat import (
    FINANCIAL_CHAT_SYSTEM_PROMPT,
)
from src.ai.schemas.research_schemas import (
    FilingEvidence,
    NewsEvidence,
)
from src.ai.tools.company_tools import (
    get_company_core_research_data,
)
from src.ai.tools.filing_tools import (
    get_filing_evidence,
)
from src.ai.tools.news_tools import (
    get_news_evidence,
)


# ---------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------


financial_chat_agent = Agent(
    model="openai:gpt-5",
    output_type=str,
    system_prompt=FINANCIAL_CHAT_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------
# Chat-facing tool wrappers
# ---------------------------------------------------------------------


@financial_chat_agent.tool_plain
def retrieve_company_research_data(
    ticker: str,
) -> Dict[str, Any]:
    """
    Retrieve broad deterministic research data for one publicly traded company.

    Use this tool for questions involving company identity, sector, industry,
    fundamentals, financial history, growth, profitability, balance-sheet
    strength, valuation, market performance, volatility, technical indicators,
    quantitative factor scores, overall factor score, or universe rank.

    When available, the result includes the most recent quarterly factor
    snapshot dated on or before the current date. The factor snapshot may be
    absent when the company was not part of the eligible quantitative universe.

    The ticker must be the publicly traded company's stock ticker symbol.
    For example: Apple is AAPL, Microsoft is MSFT, and Robinhood is HOOD.
    """

    return get_company_core_research_data(
        ticker=ticker,
        as_of_date=date.today(),
    )


@financial_chat_agent.tool_plain
def retrieve_company_news_evidence(
    ticker: str,
) -> List[NewsEvidence]:
    """
    Retrieve the most relevant recent news evidence for one publicly traded
    company.

    Use this tool for questions involving recent developments, announcements,
    earnings news, guidance, acquisitions, partnerships, management changes,
    litigation, regulation, product launches, or other recent company events.

    The returned articles have already been ranked for company relevance and
    materiality, deduplicated, and converted into validated news evidence.

    The ticker must be the publicly traded company's stock ticker symbol.
    """

    return get_news_evidence(
        ticker=ticker,
        as_of_date=date.today(),
    )


@financial_chat_agent.tool_plain
def retrieve_company_filing_evidence(
    ticker: str,
) -> List[FilingEvidence]:
    """
    Retrieve relevant SEC filing evidence for one publicly traded company.

    Use this tool for questions involving 10-K, 10-Q, or 8-K filings, risk
    factors, management discussion and analysis, liquidity, business strategy,
    legal proceedings, material agreements, earnings disclosures, or other
    information reported to the SEC.

    The returned filings have already been selected by filing type and include
    deterministically extracted research-relevant excerpts.

    The ticker must be the publicly traded company's stock ticker symbol.
    """

    return get_filing_evidence(
        ticker=ticker,
        as_of_date=date.today(),
    )