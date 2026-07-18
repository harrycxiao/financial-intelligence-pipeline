# src/api/ai_routes.py

"""
FastAPI routes for AI-generated investment research reports.

These endpoints coordinate two stages:

1. Build a validated deterministic research context.
2. Pass that context to the appropriate LLM agent.

The API layer does not perform quantitative analysis or construct report
content directly.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from starlette.concurrency import run_in_threadpool

from src.ai.agents import (
    generate_company_report_async,
    generate_portfolio_report_async,
)
from src.ai.schemas import (
    CompanyResearchReport,
    CompanyResearchRequest,
    QuarterlyPortfolioReport,
    QuarterlyResearchRequest,
)
from src.ai.services import (
    prepare_company_research_context,
    prepare_quarterly_research_context,
)


router = APIRouter(
    prefix="/api/ai",
    tags=["AI Research"],
)


@router.post(
    "/portfolio-report",
    response_model=QuarterlyPortfolioReport,
    status_code=status.HTTP_200_OK,
    summary="Generate a quarterly portfolio research report",
)
async def create_portfolio_report(
    request: QuarterlyResearchRequest,
) -> QuarterlyPortfolioReport:
    """
    Generate an evidence-based report for a deterministic portfolio.

    The deterministic research service first:

    - runs the quantitative research pipeline;
    - selects and weights portfolio holdings;
    - retrieves company, news, and SEC-filing evidence;
    - constructs a validated PortfolioResearchContext.

    The portfolio agent then interprets that completed context and returns a
    validated QuarterlyPortfolioReport.
    """

    try:
        context = await run_in_threadpool(
            prepare_quarterly_research_context,
            request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return await generate_portfolio_report_async(
        context=context,
    )


@router.post(
    "/company-report",
    response_model=CompanyResearchReport,
    status_code=status.HTTP_200_OK,
    summary="Generate a single-company research report",
)
async def create_company_report(
    request: CompanyResearchRequest,
) -> CompanyResearchReport:
    """
    Generate an evidence-based report for one public company.

    The deterministic research service first retrieves and assembles:

    - company metadata;
    - financial history;
    - derived fundamental and market information;
    - available quantitative research;
    - news evidence;
    - SEC-filing evidence.

    The company agent then interprets that completed context and returns a
    validated CompanyResearchReport.
    """

    try:
        context = await run_in_threadpool(
            prepare_company_research_context,
            request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return await generate_company_report_async(
        context=context,
    )


__all__ = [
    "router",
]