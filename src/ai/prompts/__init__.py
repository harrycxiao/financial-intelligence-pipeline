"""
Public exports for AI prompts.
"""

from .company_research import (
    COMPANY_REPORT_REPAIR_PROMPT,
    COMPANY_REPORT_SYSTEM_PROMPT,
    COMPANY_REPORT_USER_PROMPT,
    build_company_report_user_prompt,
)

from .portfolio_report import (
    PORTFOLIO_REPORT_REPAIR_PROMPT,
    PORTFOLIO_REPORT_SYSTEM_PROMPT,
    PORTFOLIO_REPORT_USER_PROMPT,
    build_portfolio_report_user_prompt,
)

__all__ = [
    # Portfolio prompts
    "PORTFOLIO_REPORT_SYSTEM_PROMPT",
    "PORTFOLIO_REPORT_USER_PROMPT",
    "PORTFOLIO_REPORT_REPAIR_PROMPT",
    "build_portfolio_report_user_prompt",

    # Company prompts
    "COMPANY_REPORT_SYSTEM_PROMPT",
    "COMPANY_REPORT_USER_PROMPT",
    "COMPANY_REPORT_REPAIR_PROMPT",
    "build_company_report_user_prompt",
]